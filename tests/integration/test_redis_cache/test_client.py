"""Redis cache client integration tests."""

import pytest

from redis_cache import RedisCacheClient


class TestRedisCacheConnection:
    """Test Redis cache connection and basic operations."""

    def test_settings(self, redis_client: RedisCacheClient):
        """Test Redis cache settings."""

        print(redis_client._settings)

    @pytest.mark.asyncio
    async def test_connect_success(self, redis_client: RedisCacheClient):
        """Test successful connection to Redis server."""
        # Client should already be connected via fixture
        assert redis_client._client is not None
        assert redis_client._pool is not None

        # Test ping to verify connection
        await redis_client._client.ping()

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, redis_client: RedisCacheClient):
        """Test connecting when already connected doesn't raise error."""
        # Should not raise any exception
        await redis_client.connect()
        assert redis_client._client is not None

    @pytest.mark.asyncio
    async def test_close_connection(self):
        """Test closing Redis connection."""
        client = RedisCacheClient()
        await client.connect()

        # Verify client is connected
        assert client._client is not None
        assert client._pool is not None

        # Close connection
        await client.close()

        # Verify client is disconnected
        assert client._client is None
        assert client._pool is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test Redis client context manager."""
        async with RedisCacheClient() as client:
            assert client._client is not None
            assert client._pool is not None
            # Test basic operation
            await client.set('test_key', 'test_value', ttl=10)
            value = await client.get('test_key')
            assert value == 'test_value'

        # After context manager, client should be closed
        assert client._client is None
        assert client._pool is None


class TestRedisCacheBasicOperations:
    """Test basic Redis cache operations (set/get)."""

    @pytest.mark.asyncio
    async def test_set_and_get_string(self, redis_client: RedisCacheClient):
        """Test setting and getting a string value."""
        key = 'test_string_key'
        value = 'Hello, World!'

        # Set value
        result = await redis_client.set(key, value)
        assert result is True

        # Get value
        retrieved_value = await redis_client.get(key)
        assert retrieved_value == value

    @pytest.mark.asyncio
    async def test_set_and_get_json_data(self, redis_client: RedisCacheClient):
        """Test setting and getting JSON serializable data."""
        key = 'test_json_key'
        value = {'name': 'John Doe', 'age': 30, 'city': 'Seoul', 'preferences': ['red', 'blue', 'green']}

        # Set value
        result = await redis_client.set(key, value)
        assert result is True

        # Get value
        retrieved_value = await redis_client.get(key)
        assert retrieved_value == value

    # @pytest.mark.asyncio
    # async def test_set_with_custom_ttl(self, redis_client: RedisCacheClient):
    #     """Test setting value with custom TTL."""
    #     key = 'test_ttl_key'
    #     value = 'temporary_value'
    #     ttl = 5  # 5 seconds

    #     # Set value with TTL
    #     result = await redis_client.set(key, value, ttl=ttl)
    #     assert result is True

    #     # Verify TTL is set
    #     remaining_ttl = await redis_client.ttl(key)
    #     assert 0 < remaining_ttl <= ttl

    #     # Get value immediately
    #     retrieved_value = await redis_client.get(key)
    #     assert retrieved_value == value

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, redis_client: RedisCacheClient):
        """Test getting a key that doesn't exist."""
        key = 'nonexistent_key'

        retrieved_value = await redis_client.get(key)
        assert retrieved_value is None

    @pytest.mark.asyncio
    async def test_set_without_serialization(self, redis_client: RedisCacheClient):
        """Test setting value without JSON serialization."""
        key = 'test_raw_key'
        value = '{"raw": "json", "string": true}'

        # Set value without serialization
        result = await redis_client.set(key, value, serialize=False)
        assert result is True

        # Get value without deserialization
        retrieved_value = await redis_client.get(key, deserialize=False)
        assert retrieved_value == value

    @pytest.mark.asyncio
    async def test_key_prefixing(self, redis_client: RedisCacheClient):
        """Test that keys are properly prefixed."""
        key = 'test_prefix_key'
        value = 'test_value'

        # Set value
        result = await redis_client.set(key, value)
        assert result is True

        # Check that the actual Redis key includes the prefix
        prefixed_key = redis_client._make_key(key)
        assert prefixed_key.startswith(redis_client._settings.KEY_PREFIX)

        # Verify the key exists in Redis directly
        if redis_client._client:
            exists = await redis_client._client.exists(prefixed_key)
            assert exists > 0


class TestRedisCacheDeleteExists:
    """Test delete and exists operations."""

    @pytest.mark.asyncio
    async def test_exists_existing_key(self, redis_client: RedisCacheClient):
        """Test checking existence of an existing key."""
        key = 'test_exists_key'
        value = 'test_value'

        # First, set a value
        await redis_client.set(key, value)

        # Check if key exists
        exists = await redis_client.exists(key)
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_nonexistent_key(self, redis_client: RedisCacheClient):
        """Test checking existence of a nonexistent key."""
        key = 'nonexistent_exists_key'

        # Check if key exists
        exists = await redis_client.exists(key)
        assert exists is False

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, redis_client: RedisCacheClient):
        """Test deleting an existing key."""
        key = 'test_delete_key'
        value = 'test_value'

        # Set a value
        await redis_client.set(key, value)

        # Verify key exists
        exists_before = await redis_client.exists(key)
        assert exists_before is True

        # Delete the key
        deleted = await redis_client.delete(key)
        assert deleted is True

        # Verify key no longer exists
        exists_after = await redis_client.exists(key)
        assert exists_after is False

        # Verify value is gone
        retrieved_value = await redis_client.get(key)
        assert retrieved_value is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, redis_client: RedisCacheClient):
        """Test deleting a nonexistent key."""
        key = 'nonexistent_delete_key'

        # Try to delete nonexistent key
        deleted = await redis_client.delete(key)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_operation_failure_handling(self):
        """Test error handling for delete when client is not connected."""
        client = RedisCacheClient()

        # Try to delete without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.delete('test_key')

    @pytest.mark.asyncio
    async def test_exists_operation_failure_handling(self):
        """Test error handling for exists when client is not connected."""
        client = RedisCacheClient()

        # Try to check exists without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.exists('test_key')

    @pytest.mark.asyncio
    async def test_workflow_set_exists_get_delete(self, redis_client: RedisCacheClient):
        """Test complete workflow: set -> exists -> get -> delete."""
        key = 'workflow_test_key'
        value = {'step': 'workflow_test'}

        # Step 1: Set value
        set_result = await redis_client.set(key, value)
        assert set_result is True

        # Step 2: Check exists
        exists_result = await redis_client.exists(key)
        assert exists_result is True

        # Step 3: Get value
        retrieved_value = await redis_client.get(key)
        assert retrieved_value == value

        # Step 4: Delete
        delete_result = await redis_client.delete(key)
        assert delete_result is True

        # Step 5: Verify deleted
        final_exists = await redis_client.exists(key)
        assert final_exists is False

        final_value = await redis_client.get(key)
        assert final_value is None


# class TestRedisCacheExpiration:
#     """Test expiration and TTL operations."""

#     # @pytest.mark.asyncio
#     # async def test_ttl_no_expiration(self, redis_client: RedisCacheClient):
#     #     """Test TTL for a key with no expiration set."""
#     #     key = 'test_no_ttl_key'
#     #     value = 'no_expiration_value'

#     #     # Set value without TTL
#     #     await redis_client.set(key, value)

#     #     # Check TTL
#     #     ttl = await redis_client.ttl(key)
#     #     assert ttl == -1  # No expiration

#     @pytest.mark.asyncio
#     async def test_ttl_nonexistent_key(self, redis_client: RedisCacheClient):
#         """Test TTL for a nonexistent key."""
#         key = 'nonexistent_ttl_key'

#         ttl = await redis_client.ttl(key)
#         assert ttl == -2  # Key doesn't exist

#     @pytest.mark.asyncio
#     async def test_expire_key(self, redis_client: RedisCacheClient):
#         """Test setting expiration on an existing key."""
#         key = 'test_expire_key'
#         value = 'expire_test_value'
#         initial_ttl = 10

#         # Set value
#         await redis_client.set(key, value)

#         # Set expiration
#         expire_result = await redis_client.expire(key, initial_ttl)
#         assert expire_result is True

#         # Check TTL is set
#         ttl = await redis_client.ttl(key)
#         assert 0 < ttl <= initial_ttl

#     @pytest.mark.asyncio
#     async def test_expire_nonexistent_key(self, redis_client: RedisCacheClient):
#         """Test setting expiration on a nonexistent key."""
#         key = 'nonexistent_expire_key'

#         expire_result = await redis_client.expire(key, 10)
#         assert expire_result is False

#     @pytest.mark.asyncio
#     async def test_key_expiration_workflow(self, redis_client: RedisCacheClient):
#         """Test complete expiration workflow."""
#         key = 'test_expiration_workflow'
#         value = 'will_expire'
#         short_ttl = 2  # 2 seconds

#         # Set value with short TTL
#         await redis_client.set(key, value, ttl=short_ttl)

#         # Verify key exists and has TTL
#         exists_before = await redis_client.exists(key)
#         assert exists_before is True

#         ttl_before = await redis_client.ttl(key)
#         assert 0 < ttl_before <= short_ttl

#         # Get value before expiration
#         value_before = await redis_client.get(key)
#         assert value_before == value

#         # Wait for expiration
#         await asyncio.sleep(short_ttl + 1)

#         # Verify key no longer exists after expiration
#         exists_after = await redis_client.exists(key)
#         assert exists_after is False

#         # Verify value is gone
#         value_after = await redis_client.get(key)
#         assert value_after is None

#         # Verify TTL is -2 (key doesn't exist)
#         ttl_after = await redis_client.ttl(key)
#         assert ttl_after == -2

#     @pytest.mark.asyncio
#     async def test_extend_expiration(self, redis_client: RedisCacheClient):
#         """Test extending expiration time of a key."""
#         key = 'test_extend_key'
#         value = 'extend_test'
#         initial_ttl = 3
#         extended_ttl = 8

#         # Set value with initial TTL
#         await redis_client.set(key, value, ttl=initial_ttl)

#         # Verify initial TTL
#         initial_ttl_check = await redis_client.ttl(key)
#         assert 0 < initial_ttl_check <= initial_ttl

#         # Extend expiration
#         extend_result = await redis_client.expire(key, extended_ttl)
#         assert extend_result is True

#         # Verify extended TTL
#         extended_ttl_check = await redis_client.ttl(key)
#         assert 0 < extended_ttl_check <= extended_ttl
#         assert extended_ttl_check > initial_ttl_check

#     @pytest.mark.asyncio
#     async def test_expire_operation_failure_handling(self):
#         """Test error handling for expire when client is not connected."""
#         client = RedisCacheClient()

#         # Try to expire without connecting
#         with pytest.raises(RuntimeError, match='Redis client not connected'):
#             await client.expire('test_key', 10)

#     @pytest.mark.asyncio
#     async def test_ttl_operation_failure_handling(self):
#         """Test error handling for ttl when client is not connected."""
#         client = RedisCacheClient()

#         # Try to get TTL without connecting
#         with pytest.raises(RuntimeError, match='Redis client not connected'):
#             await client.ttl('test_key')


class TestRedisCachePatternOperations:
    """Test pattern-based operations like clear_pattern."""

    @pytest.mark.asyncio
    async def test_clear_pattern_specific_keys(self, redis_client: RedisCacheClient):
        """Test clearing keys matching a specific pattern."""
        # Setup test keys
        test_keys = ['user:123', 'user:456', 'user:789', 'product:abc', 'product:def']

        # Set test data
        for key in test_keys:
            await redis_client.set(key, f'value_for_{key}')

        # Verify all keys exist
        for key in test_keys:
            exists = await redis_client.exists(key)
            assert exists is True

        # Clear only user keys
        deleted_count = await redis_client.clear_pattern('user:*')
        assert deleted_count == 3

        # Verify user keys are gone
        for key in ['user:123', 'user:456', 'user:789']:
            exists = await redis_client.exists(key)
            assert exists is False

        # Verify product keys still exist
        for key in ['product:abc', 'product:def']:
            exists = await redis_client.exists(key)
            assert exists is True

    @pytest.mark.asyncio
    async def test_clear_pattern_all_keys(self, redis_client: RedisCacheClient):
        """Test clearing all keys with wildcard pattern."""
        # Setup test keys
        test_keys = ['key1', 'key2', 'key3', 'another_key', 'final_key']

        # Set test data
        for key in test_keys:
            await redis_client.set(key, f'value_{key}')

        # Clear all keys
        deleted_count = await redis_client.clear_pattern('*')
        assert deleted_count == len(test_keys)

        # Verify all keys are gone
        for key in test_keys:
            exists = await redis_client.exists(key)
            assert exists is False

    @pytest.mark.asyncio
    async def test_clear_pattern_no_matches(self, redis_client: RedisCacheClient):
        """Test clearing pattern that matches no keys."""
        # Set some keys
        await redis_client.set('existing_key', 'value')

        # Try to clear non-matching pattern
        deleted_count = await redis_client.clear_pattern('nonexistent:*')
        assert deleted_count == 0

        # Verify existing key still exists
        exists = await redis_client.exists('existing_key')
        assert exists is True

    @pytest.mark.asyncio
    async def test_clear_pattern_complex_pattern(self, redis_client: RedisCacheClient):
        """Test clearing with complex pattern matching."""
        # Setup test keys with different patterns
        test_keys = [
            'session:user:123:token',
            'session:user:456:token',
            'session:admin:789:token',
            'cache:products:list',
            'cache:products:details:123',
            'temp:file:upload:abc',
            'temp:file:upload:def',
        ]

        # Set test data
        for key in test_keys:
            await redis_client.set(key, f'value_{key}')

        # Clear session tokens
        deleted_count = await redis_client.clear_pattern('session:*:token')
        assert deleted_count == 3

        # Clear cache products
        deleted_count = await redis_client.clear_pattern('cache:products:*')
        assert deleted_count == 2

        # Verify remaining keys
        remaining_keys = ['temp:file:upload:abc', 'temp:file:upload:def']
        for key in remaining_keys:
            exists = await redis_client.exists(key)
            assert exists is True

        # Verify cleared keys are gone
        cleared_keys = [
            'session:user:123:token',
            'session:user:456:token',
            'session:admin:789:token',
            'cache:products:list',
            'cache:products:details:123',
        ]
        for key in cleared_keys:
            exists = await redis_client.exists(key)
            assert exists is False

    @pytest.mark.asyncio
    async def test_clear_pattern_empty_cache(self, redis_client: RedisCacheClient):
        """Test clearing pattern when cache is empty."""
        # Clear all first to ensure empty
        await redis_client.clear_pattern('*')

        # Try to clear pattern on empty cache
        deleted_count = await redis_client.clear_pattern('any:*')
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_clear_pattern_operation_failure_handling(self):
        """Test error handling for clear_pattern when client is not connected."""
        client = RedisCacheClient()

        # Try to clear pattern without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.clear_pattern('test:*')


class TestRedisCacheJSONOperations:
    """Test Redis JSON data type operations."""

    @pytest.mark.asyncio
    async def test_json_set_and_get_object(self, redis_client: RedisCacheClient):
        """Test setting and getting a JSON object."""
        key = 'test_json_object'
        value = {'name': 'John Doe', 'age': 30, 'city': 'Seoul', 'hobbies': ['reading', 'coding']}

        # Set JSON value
        result = await redis_client.json_set(key, value)
        assert result is True

        # Get JSON value
        retrieved_value = await redis_client.json_get(key)
        assert retrieved_value == value

    @pytest.mark.asyncio
    async def test_json_set_and_get_array(self, redis_client: RedisCacheClient):
        """Test setting and getting a JSON array."""
        key = 'test_json_array'
        value = [1, 2, 3, 'four', {'five': 5}]

        # Set JSON array
        result = await redis_client.json_set(key, value)
        assert result is True

        # Get JSON array
        retrieved_value = await redis_client.json_get(key)
        assert retrieved_value == value

    @pytest.mark.asyncio
    async def test_json_set_with_ttl(self, redis_client: RedisCacheClient):
        """Test setting JSON value with TTL."""
        key = 'test_json_ttl'
        value = {'temporary': 'data'}
        ttl = 10

        # Set JSON with TTL
        result = await redis_client.json_set(key, value, ttl=ttl)
        assert result is True

        # Verify value exists
        retrieved_value = await redis_client.json_get(key)
        assert retrieved_value == value

        # Verify TTL is set (using Redis client directly)
        prefixed_key = redis_client._make_key(key)
        remaining_ttl = await redis_client._client.ttl(prefixed_key)
        assert 0 < remaining_ttl <= ttl

    @pytest.mark.asyncio
    async def test_json_set_with_path(self, redis_client: RedisCacheClient):
        """Test setting value at specific JSON path."""
        key = 'test_json_path'

        # First, set initial object
        initial_value = {'user': {'name': 'John', 'age': 30}}
        await redis_client.json_set(key, initial_value)

        # Update specific path
        await redis_client.json_set(key, 31, path='$.user.age')

        # Get entire object
        retrieved_value = await redis_client.json_get(key)
        assert isinstance(retrieved_value, dict)
        assert retrieved_value['user']['age'] == 31
        assert retrieved_value['user']['name'] == 'John'

    @pytest.mark.asyncio
    async def test_json_get_with_path(self, redis_client: RedisCacheClient):
        """Test getting value from specific JSON path."""
        key = 'test_json_get_path'
        value = {'user': {'name': 'Jane', 'profile': {'email': 'jane@example.com', 'verified': True}}}

        await redis_client.json_set(key, value)

        # Get value at specific path
        name = await redis_client.json_get(key, path='$.user.name')
        assert name == ['Jane']  # JSONPath returns list

        email = await redis_client.json_get(key, path='$.user.profile.email')
        assert email == ['jane@example.com']

    @pytest.mark.asyncio
    async def test_json_get_nonexistent_key(self, redis_client: RedisCacheClient):
        """Test getting a JSON key that doesn't exist."""
        key = 'nonexistent_json_key'

        retrieved_value = await redis_client.json_get(key)
        assert retrieved_value is None

    @pytest.mark.asyncio
    async def test_json_mget_multiple_keys(self, redis_client: RedisCacheClient):
        """Test getting multiple JSON values at once."""
        keys = ['json_user1', 'json_user2', 'json_user3']
        values = [
            {'name': 'User1', 'age': 25},
            {'name': 'User2', 'age': 30},
            {'name': 'User3', 'age': 35},
        ]

        # Set multiple JSON values
        for key, value in zip(keys, values, strict=False):
            await redis_client.json_set(key, value)

        # Get multiple values at once
        retrieved_values = await redis_client.json_mget(keys)
        assert retrieved_values == values

    @pytest.mark.asyncio
    async def test_json_mget_with_nonexistent_keys(self, redis_client: RedisCacheClient):
        """Test mget with some nonexistent keys."""
        keys = ['json_exists1', 'json_nonexistent', 'json_exists2']

        # Set only some keys
        await redis_client.json_set('json_exists1', {'data': 1})
        await redis_client.json_set('json_exists2', {'data': 2})

        # Get multiple values
        retrieved_values = await redis_client.json_mget(keys)
        assert retrieved_values[0] == {'data': 1}
        assert retrieved_values[1] is None
        assert retrieved_values[2] == {'data': 2}

    @pytest.mark.asyncio
    async def test_json_delete_entire_key(self, redis_client: RedisCacheClient):
        """Test deleting entire JSON key."""
        key = 'test_json_delete'
        value = {'data': 'to_be_deleted'}

        # Set JSON value
        await redis_client.json_set(key, value)

        # Verify it exists
        retrieved_value = await redis_client.json_get(key)
        assert retrieved_value == value

        # Delete entire key
        deleted = await redis_client.json_delete(key)
        assert deleted is True

        # Verify it's gone
        retrieved_value = await redis_client.json_get(key)
        assert retrieved_value is None

    @pytest.mark.asyncio
    async def test_json_delete_specific_path(self, redis_client: RedisCacheClient):
        """Test deleting value at specific JSON path."""
        key = 'test_json_delete_path'
        value = {'user': {'name': 'John', 'age': 30, 'email': 'john@example.com'}}

        await redis_client.json_set(key, value)

        # Delete specific field
        deleted = await redis_client.json_delete(key, path='$.user.email')
        assert deleted is True

        # Verify field is gone but others remain
        retrieved_value = await redis_client.json_get(key)
        assert 'email' not in retrieved_value['user']
        assert retrieved_value['user']['name'] == 'John'
        assert retrieved_value['user']['age'] == 30

    @pytest.mark.asyncio
    async def test_json_arrappend_to_array(self, redis_client: RedisCacheClient):
        """Test appending values to JSON array."""
        key = 'test_json_array_append'
        value = {'hobbies': ['reading', 'coding']}

        await redis_client.json_set(key, value)

        # Append to array
        new_length = await redis_client.json_arrappend(key, '$.hobbies', 'gaming', 'cooking')
        assert new_length == 4

        # Verify array was updated
        retrieved_value = await redis_client.json_get(key)
        assert retrieved_value['hobbies'] == ['reading', 'coding', 'gaming', 'cooking']

    @pytest.mark.asyncio
    async def test_json_arrappend_complex_values(self, redis_client: RedisCacheClient):
        """Test appending complex values to JSON array."""
        key = 'test_json_array_complex'
        value = {'items': [{'id': 1, 'name': 'item1'}]}

        await redis_client.json_set(key, value)

        # Append complex object
        new_item = {'id': 2, 'name': 'item2'}
        new_length = await redis_client.json_arrappend(key, '$.items', new_item)
        assert new_length == 2

        # Verify array was updated
        retrieved_value = await redis_client.json_get(key)
        assert len(retrieved_value['items']) == 2
        assert retrieved_value['items'][1] == new_item

    @pytest.mark.asyncio
    async def test_json_objkeys_get_object_keys(self, redis_client: RedisCacheClient):
        """Test getting keys of a JSON object."""
        key = 'test_json_objkeys'
        value = {'name': 'John', 'age': 30, 'city': 'Seoul', 'email': 'john@example.com'}

        await redis_client.json_set(key, value)

        # Get object keys
        keys = await redis_client.json_objkeys(key)
        assert set(keys) == {'name', 'age', 'city', 'email'}

    @pytest.mark.asyncio
    async def test_json_objkeys_nested_path(self, redis_client: RedisCacheClient):
        """Test getting keys of nested JSON object."""
        key = 'test_json_objkeys_nested'
        value = {'user': {'profile': {'name': 'Jane', 'age': 25}, 'settings': {'theme': 'dark'}}}

        await redis_client.json_set(key, value)

        # Get keys of nested object
        profile_keys = await redis_client.json_objkeys(key, path='$.user.profile')
        assert set(profile_keys) == {'name', 'age'}

        settings_keys = await redis_client.json_objkeys(key, path='$.user.settings')
        assert settings_keys == ['theme']

    @pytest.mark.asyncio
    async def test_json_type_various_types(self, redis_client: RedisCacheClient):
        """Test getting type of various JSON values."""
        # Test object type
        key1 = 'test_json_type_object'
        await redis_client.json_set(key1, {'name': 'John'})
        type1 = await redis_client.json_type(key1)
        assert type1 == 'object'

        # Test array type
        key2 = 'test_json_type_array'
        await redis_client.json_set(key2, [1, 2, 3])
        type2 = await redis_client.json_type(key2)
        assert type2 == 'array'

        # Test string type
        key3 = 'test_json_type_string'
        await redis_client.json_set(key3, 'hello')
        type3 = await redis_client.json_type(key3)
        assert type3 == 'string'

        # Test number type
        key4 = 'test_json_type_number'
        await redis_client.json_set(key4, 42)
        type4 = await redis_client.json_type(key4)
        assert type4 == 'integer'

        # Test boolean type
        key5 = 'test_json_type_boolean'
        await redis_client.json_set(key5, True)
        type5 = await redis_client.json_type(key5)
        assert type5 == 'boolean'

    @pytest.mark.asyncio
    async def test_json_type_with_path(self, redis_client: RedisCacheClient):
        """Test getting type of value at specific path."""
        key = 'test_json_type_path'
        value = {'user': {'name': 'John', 'age': 30, 'hobbies': ['reading', 'coding']}}

        await redis_client.json_set(key, value)

        # Check types at different paths
        name_type = await redis_client.json_type(key, path='$.user.name')
        assert name_type == 'string'

        age_type = await redis_client.json_type(key, path='$.user.age')
        assert age_type == 'integer'

        hobbies_type = await redis_client.json_type(key, path='$.user.hobbies')
        assert hobbies_type == 'array'

    @pytest.mark.asyncio
    async def test_json_complex_nested_structure(self, redis_client: RedisCacheClient):
        """Test working with complex nested JSON structure."""
        key = 'test_json_complex'
        value = {
            'company': 'TechCorp',
            'employees': [
                {'id': 1, 'name': 'Alice', 'department': 'Engineering', 'skills': ['Python', 'Go']},
                {'id': 2, 'name': 'Bob', 'department': 'Design', 'skills': ['Figma', 'Photoshop']},
            ],
            'metadata': {'founded': 2020, 'location': 'Seoul', 'active': True},
        }

        # Set complex structure
        await redis_client.json_set(key, value)

        # Get entire structure
        retrieved_value = await redis_client.json_get(key)
        assert retrieved_value == value

        # Get specific nested value
        first_employee = await redis_client.json_get(key, path='$.employees[0]')
        assert first_employee[0]['name'] == 'Alice'

        # Update nested value
        await redis_client.json_set(key, 'Marketing', path='$.employees[1].department')

        # Verify update
        updated_value = await redis_client.json_get(key)
        assert updated_value['employees'][1]['department'] == 'Marketing'

        # Append to nested array
        await redis_client.json_arrappend(key, '$.employees[0].skills', 'Rust')
        updated_value = await redis_client.json_get(key)
        assert 'Rust' in updated_value['employees'][0]['skills']

    @pytest.mark.asyncio
    async def test_json_workflow_complete(self, redis_client: RedisCacheClient):
        """Test complete JSON workflow with multiple operations."""
        key = 'test_json_workflow'

        # 1. Create initial object
        initial_data = {'cart': {'items': [], 'total': 0}}
        await redis_client.json_set(key, initial_data)

        # 2. Verify structure
        cart_type = await redis_client.json_type(key, path='$.cart')
        assert cart_type == 'object'

        items_type = await redis_client.json_type(key, path='$.cart.items')
        assert items_type == 'array'

        # 3. Add items to cart
        item1 = {'id': 'prod1', 'name': 'Product 1', 'price': 100}
        item2 = {'id': 'prod2', 'name': 'Product 2', 'price': 200}
        await redis_client.json_arrappend(key, '$.cart.items', item1, item2)

        # 4. Update total
        await redis_client.json_set(key, 300, path='$.cart.total')

        # 5. Verify final state
        final_data = await redis_client.json_get(key)
        assert len(final_data['cart']['items']) == 2
        assert final_data['cart']['total'] == 300

        # 6. Get object keys
        cart_keys = await redis_client.json_objkeys(key, path='$.cart')
        assert set(cart_keys) == {'items', 'total'}

        # 7. Delete key
        deleted = await redis_client.json_delete(key)
        assert deleted is True

        # 8. Verify deletion
        final_value = await redis_client.json_get(key)
        assert final_value is None

    @pytest.mark.asyncio
    async def test_json_operation_failure_handling(self):
        """Test error handling for JSON operations when client is not connected."""
        client = RedisCacheClient()

        # Test json_set without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.json_set('test_key', {'data': 'value'})

        # Test json_get without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.json_get('test_key')

        # Test json_mget without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.json_mget(['key1', 'key2'])

        # Test json_delete without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.json_delete('test_key')

        # Test json_arrappend without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.json_arrappend('test_key', '$.array', 'value')

        # Test json_objkeys without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.json_objkeys('test_key')

        # Test json_type without connecting
        with pytest.raises(RuntimeError, match='Redis client not connected'):
            await client.json_type('test_key')
