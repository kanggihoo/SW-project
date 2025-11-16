"""
Product Adapter: Service layer's raw data to LLM-friendly format

Transforms dict-format raw data returned by Service (MusinsaAPIWrapper)
into concise str or dict format that LLM can directly use.
"""

from typing import Any


class ProductAdapter:
    """
    Adapter that transforms MusinsaAPIWrapper (Service) response data into LLM-friendly format.
    All methods are static methods, focusing only on data transformation.
    """

    @staticmethod
    def adapt_size_recommend(raw_data: dict[str, Any]) -> str:
        """Transform size recommendation data into LLM-friendly string

        Args:
            raw_data: Raw dict returned from Service
                Example: {'success': True, 'data': [...], 'message': '...'}

        Returns:
            str: Summary string ready for LLM consumption
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Size recommendation information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        size_recommends = raw_data['data']
        if not size_recommends:
            return 'No size recommendation data available for the given criteria.'

        # Sort recommendations by percentage
        sorted_recommends = sorted(size_recommends, key=lambda x: x.get('percent', 0), reverse=True)

        # Transform to "M (45.2%, 123 people), L (30.1%, 82 people)" format
        recommend_strings = [f'{item["size"]} ({item["percent"]}%, {item["count"]} people)' for item in sorted_recommends]

        return f'Size recommendations: {", ".join(recommend_strings)}'

    @staticmethod
    def adapt_selection_info(raw_data: dict[str, Any]) -> str | dict[str, Any]:
        """Transform product selection option info into LLM-friendly format

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            str | dict: Concise option information
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Selection option information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        option_info = raw_data['data'][0]
        option_count = option_info.get('option_count', 0)

        if option_count == 0:
            return 'This product has no selection options.'

        # When there are 2+ options (e.g., color + size)
        if option_count > 1:
            first_options = [opt['name'] for opt in option_info.get('first_options', [])]
            secondary_options = [opt['name'] for opt in option_info.get('secondary_options', [])]

            result = {
                'message': f'This product has {option_count} option types.',
                'first_option': {
                    'name': option_info.get('first_option_name', 'Option 1'),
                    'values': first_options,
                },
                'secondary_option': {
                    'name': option_info.get('secondary_option_name', 'Option 2'),
                    'values': secondary_options,
                },
            }
            return result

        # When there's only 1 option type
        first_options = [opt['name'] for opt in option_info.get('first_options', [])]
        option_name = option_info.get('first_option_name', 'Option')

        return f'{option_name}: {", ".join(first_options)}'

    @staticmethod
    def adapt_option_stock(raw_data: dict[str, Any]) -> dict[str, Any] | str:
        """Transform stock info by option into LLM-friendly format

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            dict | str: Option types + stock status map
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Stock information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        stock_info = raw_data['data'][0]
        option_filters = stock_info.get('option_filters', [])
        stock_by_options = stock_info.get('stock_by_options', [])

        # Extract option types (e.g., [{"name": "Color", "values": ["Black", "White"]}, ...])
        option_types = [{'name': opt['name'], 'values': [val['name'] for val in opt.get('values', [])]} for opt in option_filters]

        # Create stock status map (e.g., {"Black, S": "Sold out", "Black, M": "Available"})
        stock_status = {}
        for stock_item in stock_by_options:
            option_key = ', '.join(stock_item.get('option_combination', []))
            status = 'Sold out' if stock_item.get('is_sold_out') else 'Available'
            stock_status[option_key] = status

        return {'option_types': option_types, 'stock_status': stock_status}

    @staticmethod
    def adapt_size_details(raw_data: dict[str, Any]) -> list[dict[str, Any]] | str:
        """Transform detailed size measurements into LLM-friendly format

        Args:
            raw_data: Raw dict returned from Service
        Returns:
            list[dict] | str: List of measurements by size
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Detailed size information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        product_info = raw_data['data'][0]
        size_details_list = product_info.get('size_details', [])

        if not size_details_list:
            return 'No detailed size information available for this product.'

        # [{"size_name": "S", "measurements": {"Total length": 69, "Shoulder width": 46.5}}, ...]
        processed = []
        for size_detail in size_details_list:
            size_name = size_detail.get('size_name')
            measurements = {item['name']: item['value'] for item in size_detail.get('items', [])}

            processed.append({'size_name': size_name, 'measurements': measurements})

        return processed

    @staticmethod
    def adapt_review_summary(raw_data: dict[str, Any]) -> str:
        """Transform review summary info into LLM-friendly string

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            str: Review summary string
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Review summary information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        summary_info = raw_data['data'][0]
        total_count = summary_info.get('total_review_count', 0)
        style_count = summary_info.get('style_review_count', 0)
        monthly_count = summary_info.get('monthly_review_count', 0)
        general_count = summary_info.get('general_review_count', 0)
        avg_rating = summary_info.get('average_rating', 0.0)

        return (
            f'Review summary: Total of {total_count:,} reviews with average rating of {avg_rating} stars. '
            f'(Style reviews: {style_count:,}, Monthly reviews: {monthly_count:,}, General reviews: {general_count:,})'
        )

    @staticmethod
    def adapt_filtered_review_count(
        raw_data: dict[str, Any], has_photo: bool = False, option_list: list[str] | None = None, sex: str | None = None
    ) -> str:
        """Transform filtered review count into LLM-friendly string

        Args:
            raw_data: Raw dict returned from Service
            has_photo: Whether photo is included (for filter description)
            option_list: Option list (for filter description)
            sex: Gender (for filter description)

        Returns:
            str: Filtered review count description string
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Review count information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        count = raw_data['data'][0].get('count', 0)

        # Generate filter condition descriptions
        filter_descriptions = []
        if has_photo:
            filter_descriptions.append('with photo')
        if option_list:
            filter_descriptions.append(f'options: {", ".join(option_list)}')
        if sex == 'M':
            filter_descriptions.append('gender: male')
        elif sex == 'F':
            filter_descriptions.append('gender: female')

        if not filter_descriptions:
            return f'Total review count for this product is {count:,}.'
        else:
            context_str = ', '.join(filter_descriptions)
            return f'Reviews matching criteria ({context_str}): {count:,} total.'

    @staticmethod
    def adapt_review_list(raw_data: dict[str, Any]) -> list[dict[str, Any]] | str:
        """Transform detailed review list into LLM-friendly format

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            list[dict] | str: Concise review info list
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Review list not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        reviews = raw_data['data']

        if not reviews:
            return 'No reviews match the criteria.'

        # Extract core information into concise format
        processed_reviews = []
        for review in reviews:
            user_info = review.get('user_info', {})

            # Generate user spec string ("M, 175cm, 70kg")
            spec_parts = []
            if user_info.get('sex'):
                spec_parts.append(user_info['sex'])
            if user_info.get('height_cm'):
                spec_parts.append(f'{user_info["height_cm"]}cm')
            if user_info.get('weight_kg'):
                spec_parts.append(f'{user_info["weight_kg"]}kg')

            author_spec = ', '.join(spec_parts) if spec_parts else 'No info'

            # Simplify date format
            created_at = review.get('created_at', '')
            date = created_at.split('T')[0] if 'T' in created_at else created_at

            processed_reviews.append(
                {
                    'rating': review.get('rating'),
                    'likes': review.get('like_count'),
                    'option': review.get('goods_option'),
                    'date': date,
                    'author': author_spec,
                    'content': review.get('content'),
                }
            )

        return processed_reviews

    @staticmethod
    def adapt_product_like_count(raw_data: dict[str, Any]) -> str:
        """Transform product like count into LLM-friendly string

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            str: Like count description string
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Like count information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        data = raw_data['data']

        # Single product case
        if len(data) == 1:
            count = data[0].get('count', 0)
            return f'This product has {count:,} likes.'

        # Multiple products case
        like_strings = [f'Product {item.get("product_id")} ({item.get("count", 0):,} likes)' for item in data]
        return f'Like count by product: {", ".join(like_strings)}'

    @staticmethod
    def adapt_product_stats(raw_data: dict[str, Any]) -> str:
        """Transform product stats (views, sales) into LLM-friendly string

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            str: Statistics info string
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Statistics information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        stats_info = raw_data['data'][0]
        views = stats_info.get('product_view_total', 0)
        purchases = stats_info.get('purchase_total', 0)

        return f'Product stats: {views:,} views in the past month, {purchases:,} total sales.'

    @staticmethod
    def adapt_other_color_products(raw_data: dict[str, Any]) -> list[dict[str, Any]] | str:
        """Transform other color product info into LLM-friendly format

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            list[dict] | str: Other color product info list
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Other color product information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        products = raw_data['data']

        if not products:
            return 'No other color products available.'

        # Transform into concise format
        color_products = []
        for product in products:
            color_products.append(
                {
                    'product_id': product.get('product_id'),
                    'name': product.get('goods_name'),
                    'status': 'Sold out' if product.get('is_sold_out') else 'Available',
                    # 'image_url': product.get('image_url'),
                }
            )

        return color_products

    @staticmethod
    def adapt_brand_and_price(raw_data: dict[str, Any]) -> dict[str, Any] | str:
        """Transform brand and price info into structured data (with optional summary text)

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            dict | str: {
                'brand_name': str,
                'price_info': {
                    'sale_price': str,
                    'original_price': str,
                    'discount_rate': str,
                    'is_on_sale': bool,
                },

            }
            또는 에러 발생 시 에러 메시지 문자열
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Brand and price information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        info = raw_data['data'][0]
        brand_info = info.get('brand_info', {})
        price_info = info.get('price_info', {})

        brand_name = brand_info.get('brand_name', 'Unknown')
        sale_price = price_info.get('sale_price', 0)
        original_price = price_info.get('original_price', 0)
        discount_rate = price_info.get('discount_rate', 0)
        is_on_sale = price_info.get('is_on_sale', False)

        # Generate price info string (요약용)
        if is_on_sale and discount_rate > 0:
            price_str = f'Currently on sale: {discount_rate}% off, priced at {sale_price:,} KRW (Original price: {original_price:,} KRW)'
        else:
            price_str = f'Regular price: {original_price:,} KRW'

        return {
            'brand_name': brand_name,
            'price_info': {
                'sale_price': f'{sale_price:,}원',
                'original_price': f'{original_price:,}원',
                'discount_rate': f'{discount_rate}%',
                'is_on_sale': is_on_sale,
            },
            'summary': f'Brand: {brand_name}\nPrice: {price_str}',
        }

    @staticmethod
    def adapt_brand_like_count(raw_data: dict[str, Any]) -> str:
        """Transform brand like count into LLM-friendly string

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            str: Brand like count string
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Brand like count information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        data = raw_data['data']

        # Single brand case
        if len(data) == 1:
            result = data[0]
            name = result.get('brand_name', 'Unknown brand')
            count = result.get('count', 0)
            return f"Brand '{name}' has {count:,} likes."

        # Multiple brands case
        like_strings = [f'{item.get("brand_name")} ({item.get("count", 0):,} likes)' for item in data]
        return f'Like count by brand: {", ".join(like_strings)}'

    @staticmethod
    def adapt_color_code(raw_data: dict[str, Any]) -> list[dict[str, Any]] | str:
        """Transform color code info into LLM-friendly format

        Args:
            raw_data: Raw dict returned from Service

        Returns:
            list[dict] | str: Color code list
        """
        if not raw_data.get('success') or not raw_data.get('data'):
            error_msg = raw_data.get('message', 'Color code information not available.')
            error_details = raw_data.get('error_details', {})
            if error_details:
                return f'{error_msg} (Error type: {error_details.get("error_type")})'
            return error_msg

        color_list = raw_data['data']

        if not color_list:
            return 'No color code information available.'

        # Return in concise format
        return [{'color_id': color['color_id'], 'color_name': color['color_name']} for color in color_list]

    @staticmethod
    def adapt_product_details(raw_data_map: dict[str, dict | None]) -> dict[str, Any]:
        """
        병렬 호출된 여러 원본 데이터를 받아,
        하나의 구조화된 딕셔너리로 조립합니다.

        Args:
            raw_data_map: 각 API 호출 결과의 매핑 딕셔너리
                {
                    'brand_and_price': {...},
                    'stats': {...},
                    'like_count': {...},
                    'selection_info': {...},
                    'other_colors': {...}
                }

        Returns:
            dict: 구조화된 제품 상세 정보
        """
        final_details: dict[str, Any] = {}

        # 1. 브랜드 및 가격 정보 처리 - 기존 어댑터 재사용
        price_data = raw_data_map.get('brand_and_price')
        if price_data:
            adapted_price = ProductAdapter.adapt_brand_and_price(price_data)
            if isinstance(adapted_price, dict):
                # 기존 테스트에서 사용하는 구조 유지
                final_details['brand_name'] = adapted_price.get('brand_name')
                final_details['price_info'] = adapted_price.get('price_info', {})

        # 2. 통계 정보 처리 (조회수/판매량 + 좋아요 수)
        statistics_parts: list[str] = []

        stats_data = raw_data_map.get('stats')
        if stats_data:
            stats_str = ProductAdapter.adapt_product_stats(stats_data)
            if isinstance(stats_str, str) and stats_str:
                statistics_parts.append(stats_str)

        like_count_data = raw_data_map.get('like_count')
        if like_count_data:
            like_str = ProductAdapter.adapt_product_like_count(like_count_data)
            if isinstance(like_str, str) and like_str:
                statistics_parts.append(like_str)

        if statistics_parts:
            # 하나의 문자열로 합쳐서 반환 (기존 테스트는 타입만 검증)
            final_details['statistics'] = ' '.join(statistics_parts)

        # 3. 구매 옵션 정보 처리 - 기존 어댑터 재사용
        selection_data = raw_data_map.get('selection_info')
        if selection_data:
            adapted_selection = ProductAdapter.adapt_selection_info(selection_data)
            final_details['options'] = adapted_selection

        # 4. 다른 색상 제품 정보 처리 - 기존 어댑터 재사용
        other_colors_data = raw_data_map.get('other_colors')
        if other_colors_data:
            adapted_other_colors = ProductAdapter.adapt_other_color_products(other_colors_data)
            final_details['other_colors'] = adapted_other_colors

        # 5. 상품 설명 정보 처리 (DB에서 온 값 그대로 사용)
        description_info = raw_data_map.get('description_info')
        if description_info is not None:
            final_details['description'] = description_info

        return final_details
