from graph.common.state import State


def route_expert_loop(state: State):
    """전문가 1명의 작업 사이클 후, 루프를 계속할지 종료할지 결정"""
    print('\n--- 라우팅(루프 제어): route_expert_loop ---')
    experts_left = state.get('experts_to_run', [])

    if len(experts_left) > 0:
        print(f'- 경로 결정: 루프 계속 (남은 전문가: {experts_left})')
        return 'continue_loop'
    else:
        print('- 경로 결정: 루프 종료 (모든 전문가 완료)')
        return 'end_loop'
