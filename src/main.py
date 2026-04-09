# Entry point for either manual pygame blackjack or autonomous SARSA runs.
# See README.md for instructions on how to run. 
# Allows either manual UI mode, or headless train.eval mode

from sarsa_agent import build_parser, run_from_args
from logger_config import set_logging_enabled


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    set_logging_enabled(not args.no_log)

    if args.mode == "ui":
        from blackjack_game import BlackjackGame

        game = BlackjackGame()
        game.run()
    else:
        run_from_args(args)
