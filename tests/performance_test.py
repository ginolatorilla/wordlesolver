from cProfile import Profile

from wordlesolver import analytics


def test_Predictor_init_performance() -> None:
    with Profile() as profiler:
        analytics.Predictor()

    profiler.print_stats(sort='time')


def test_Predictor_predict_wordle_1st_round_performance() -> None:
    predictor = analytics.Predictor()

    with Profile() as profiler:
        predictor.predict_wordle()

    profiler.print_stats(sort='time')


def test_Predictor_calibrate_performance() -> None:
    predictor = analytics.Predictor()

    with Profile() as profiler:
        predictor.calibrate('crate', 'mmmmm')

    profiler.print_stats(sort='time')