# SARSA agent train/eval using this project's pygame blackjack implementation
# models trained get output to the ./models directory under 
# `sarsa_blackjack_sarsa.pkl` . Game logic used is blackjack_game.py, game_state and
# the logger_config needs to be included.  
from __future__ import annotations

import argparse
import os
import pickle
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from game_state import GameState
from logger_config import get_logger


State = Tuple[int, int, int, int, int, int, int]
Action = int
BET_AMOUNTS = [10, 20, 50, 100, 200]
ACTION_SPACE_SIZE = 8  # 0-4 bet index, 5 hit, 6 stand, 7 split
BUDGET_BUCKET_EDGES = (50, 150, 400, 800)
DEFAULT_MODEL_PATH = str(Path(__file__).resolve().parents[1] / "models" / "sarsa_blackjack_sarsa.pkl")


def _budget_bucket(budget: int) -> int:
    for idx, edge in enumerate(BUDGET_BUCKET_EDGES):
        if budget < edge:
            return idx
    return len(BUDGET_BUCKET_EDGES)


@dataclass
class SarsaConfig:
    episodes: int = 500_000
    alpha: float = 0.05
    gamma: float = 0.99
    epsilon: float = 1.0
    epsilon_min: float = 0.05
    epsilon_decay: float = 0.999988
    eval_episodes: int = 20_000
    seed: int = 42
    starting_budget: int = 500
    max_rounds: int = 50


class PygameBlackjackEnv(gym.Env):
    """Gymnasium environment built on the custom blackjack GameState."""
    # These are the penalties and rewards enforced on the model 
    # during training/eval. If the model goes broke during a Set, 
    # it should be penalized, rewarded otherwise. 
    # When following some common strategies, it should be rewarded
    # if these strategies work and lead to a win. If a strategy is followed, 
    # and we lose, we should not be too heavily penalized. This actually ends up 
    # doing more harm in the long run, as it incentivises our model to 
    # follow these strats less and less.


    metadata = {"render_modes": []}
    SET_BROKE_PENALTY = -40.0
    SET_PROFIT_REWARD = 20.0
    SET_LOSS_PENALTY = -20.0
    STRATEGY_WIN_REWARD = 0.5
    STRATEGY_FOLLOWED_LOST_PENALTY = 0.0
    STRATEGY_NOT_FOLLOWED_PENALTY = -0.5
    BET_SIZE_RISK_THRESHOLD = 150
    BET_SIZE_RISK_PENALTY = -0.3

    def __init__(self, starting_budget: int = 500, max_rounds: int = 50):
        super().__init__()
        self.starting_budget = starting_budget
        self.max_rounds = max_rounds
        self.bet_amounts = BET_AMOUNTS
        self.logger = get_logger("sarsa_env")

        self.action_space = spaces.Discrete(ACTION_SPACE_SIZE)
        self.observation_space = spaces.MultiDiscrete(
            [4, 33, 12, 2, 2, len(BUDGET_BUCKET_EDGES) + 1, 6]
        )

        self.state = GameState(starting_budget=self.starting_budget, bet_amount=self.bet_amounts[0])
        self.rounds_played = 0
        self.round_followed_strategy = True

    def reset(self, *, seed: int | None = None, options: Dict[str, Any] | None = None):
        super().reset(seed=seed)
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.state = GameState(starting_budget=self.starting_budget, bet_amount=self.bet_amounts[0])
        self.rounds_played = 0
        self.round_followed_strategy = True
        return self._observation(), self._info()

    def step(self, action: int):
        prev_budget = self.state.budget
        prev_wins = self.state.wins
        reward = 0.0
        terminated = False
        truncated = False
        legal_actions = self._legal_actions()
        strategy_observed = False

        if self.state.game_state == "playing":
            strategy_observed = True
            recommended_action = self._recommended_strategy_action(legal_actions)
            if action != recommended_action:
                self.round_followed_strategy = False

        if action not in legal_actions:
            reward = -0.2
            self.logger.info(f"[ENV] Illegal action {action} in phase {self.state.game_state}")
            if self.state.budget < min(self.bet_amounts):
                self.state.game_state = "broke"
                terminated = True
            return self._observation(), reward, terminated, truncated, self._info()

        if self.state.game_state == "betting":
            chosen_bet = self.bet_amounts[action]
            # Apply bet-sizing risk penalty when budget is low and bet is large.
            if self.state.budget < self.BET_SIZE_RISK_THRESHOLD and chosen_bet > 20:
                reward += self.BET_SIZE_RISK_PENALTY
            self.state.bet_amount = chosen_bet

            if not self.state.place_bet():
                reward = -0.5
            else:
                self.round_followed_strategy = True
                self.state.deal_initial_hand()
                if self.state.player_hand.is_blackjack():
                    self.state.dealer_play()
                    self.state.determine_winner()

        elif self.state.game_state == "playing":
            if action == 5:  # hit
                hand_finished = self.state.player_hit()

                if self.state.is_split and hand_finished:
                    all_bust = all(hand.is_bust() for hand in self.state.split_hands)
                    if all_bust:
                        self.state.game_state = "game_over"
                        self.state.dealer_reveal = True
                        self.state.result_message = "All hands BUST!"
                        self.state.losses += len(self.state.split_hands)
                        self.state.current_bet = 0
                    else:
                        self.state.dealer_play()
                        self.state.determine_winner()

                if (
                    not self.state.is_split
                    and self.state.game_state == "playing"
                    and self.state.player_hand.get_value() == 21
                ):
                    self.state.dealer_play()
                    self.state.determine_winner()

            elif action == 6:  # stand
                self.state.dealer_play()
                self.state.determine_winner()
            elif action == 7:  # split
                if not self.state.split_hand():
                    reward -= 0.2

        if self.state.game_state == "game_over":
            round_net = self.state.budget - prev_budget
            reward += float(round_net) / 100.0

            # strategy_observed is only True for rounds that entered the "playing"
            # phase — player-blackjack auto-resolves intentionally skip this block.
            if strategy_observed:
                round_won = self.state.wins > prev_wins
                if self.round_followed_strategy:
                    if round_won:
                        reward += self.STRATEGY_WIN_REWARD
                    else:
                        reward += self.STRATEGY_FOLLOWED_LOST_PENALTY
                else:
                    reward += self.STRATEGY_NOT_FOLLOWED_PENALTY

            self.rounds_played += 1

            if self.state.budget < min(self.bet_amounts):
                self.state.game_state = "broke"
                terminated = True
            elif self.rounds_played >= self.max_rounds:
                truncated = True
            else:
                self.state.game_state = "betting"
                self.state.dealer_reveal = False
                self.state.result_message = ""
                self.round_followed_strategy = True

        if self.state.game_state == "broke":
            terminated = True

        if terminated or truncated:
            final_budget = self.state.budget
            if final_budget < min(self.bet_amounts):
                reward += self.SET_BROKE_PENALTY
            elif final_budget > self.starting_budget:
                reward += self.SET_PROFIT_REWARD
            elif final_budget < self.starting_budget:
                reward += self.SET_LOSS_PENALTY

        return self._observation(), reward, terminated, truncated, self._info()

    def _recommended_strategy_action(self, legal_actions: List[int]) -> Action:
        if not legal_actions:
            return 0

        if self.state.game_state != "playing":
            return legal_actions[0]

        hand = self._active_hand()
        dealer_value = self.state.get_dealer_visible_value()
        hand_value = hand.get_value()
        has_usable_ace = any(card.rank == "A" for card in hand.cards) and hand_value <= 21

        # Pair strategy first when split is legally possible.
        if len(hand.cards) == 2 and not self.state.is_split and hand.can_split() and 7 in legal_actions:
            pair_rank = hand.cards[0].rank
            pair_to_action = {
                "A": 7,
                "8": 7,
                "7": 7 if 2 <= dealer_value <= 7 else 5,
                "6": 7 if 2 <= dealer_value <= 6 else 5,
                "5": 5,
                "4": 7 if dealer_value in {5, 6} else 5,
                "3": 7 if 2 <= dealer_value <= 7 else 5,
                "2": 7 if 2 <= dealer_value <= 7 else 5,
                "9": 7 if 2 <= dealer_value <= 9 and dealer_value != 7 else 6,
                "10": 6,
                "J": 6,
                "Q": 6,
                "K": 6,
            }
            recommended = pair_to_action.get(pair_rank, 5)
            if recommended in legal_actions:
                return recommended

        if has_usable_ace and hand_value >= 13:
            if hand_value >= 19:
                return 6 if 6 in legal_actions else legal_actions[0]
            if hand_value == 18:
                return 5 if dealer_value >= 9 else 6
            return 5

        # Hard totals strategy (double/surrender rules approximated to hit/stand only).
        if hand_value >= 17:
            return 6 if 6 in legal_actions else legal_actions[0]
        if hand_value in {13, 14, 15, 16}:
            return 6 if 2 <= dealer_value <= 6 and 6 in legal_actions else 5
        if hand_value == 12:
            return 6 if 4 <= dealer_value <= 6 and 6 in legal_actions else 5
        return 5 if 5 in legal_actions else legal_actions[0]

    def _active_hand(self):
        if self.state.is_split and self.state.split_hands:
            return self.state.split_hands[self.state.current_hand_index]
        return self.state.player_hand

    def _legal_actions(self) -> List[int]:
        if self.state.game_state == "betting":
            return [i for i, amount in enumerate(self.bet_amounts) if self.state.budget >= amount]
        if self.state.game_state == "playing":
            actions = [5, 6]
            if not self.state.is_split and self.state.player_hand.can_split() and self.state.can_split():
                actions.append(7)
            return actions
        return []

    def _phase_id(self) -> int:
        return {"betting": 0, "playing": 1, "game_over": 2, "broke": 3}.get(self.state.game_state, 0)

    def _observation(self) -> State:
        player_total = 0
        dealer_visible = 0
        usable_ace = 0
        can_split = 0

        if self.state.game_state in {"playing", "game_over", "broke"}:
            active_hand = self._active_hand()
            player_total = min(32, active_hand.get_value())
            dealer_visible = min(11, self.state.get_dealer_visible_value())
            usable_ace = int(any(card.rank == "A" for card in active_hand.cards) and active_hand.get_value() <= 21)
            can_split = int(not self.state.is_split and self.state.player_hand.can_split() and self.state.can_split())

        bet_index = 5
        if self.state.bet_amount in self.bet_amounts:
            bet_index = self.bet_amounts.index(self.state.bet_amount)

        return (
            self._phase_id(),
            player_total,
            dealer_visible,
            usable_ace,
            can_split,
            _budget_bucket(self.state.budget),
            bet_index,
        )

    def _info(self) -> Dict[str, Any]:
        return {
            "legal_actions": self._legal_actions(),
            "budget": self.state.budget,
            "wins": self.state.wins,
            "losses": self.state.losses,
            "draws": self.state.draws,
            "rounds_played": self.rounds_played,
        }


class SarsaAgent:
    def __init__(self, alpha: float, gamma: float, epsilon: float, rng: np.random.Generator) -> None:
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.rng = rng
        self.q_table: DefaultDict[State, np.ndarray] = defaultdict(
            lambda: np.zeros(ACTION_SPACE_SIZE, dtype=np.float64)
        )

    def select_action(self, state: State, legal_actions: List[int]) -> Action:
        if not legal_actions:
            return 0
        if self.rng.random() < self.epsilon:
            return int(self.rng.choice(legal_actions))

        q_values = self.q_table[state]
        legal_q = [(a, q_values[a]) for a in legal_actions]
        max_q = max(value for _, value in legal_q)
        best_actions = [a for a, value in legal_q if value == max_q]
        return int(self.rng.choice(best_actions))

    def greedy_action(self, state: State, legal_actions: List[int]) -> Action:
        if not legal_actions:
            return 0
        q_values = self.q_table[state]
        return int(max(legal_actions, key=lambda action: q_values[action]))

    def update(
        self,
        state: State,
        action: Action,
        reward: float,
        next_state: State,
        next_action: Action,
        done: bool,
    ) -> None:
        current_q = self.q_table[state][action]
        target = reward if done else reward + self.gamma * self.q_table[next_state][next_action]
        self.q_table[state][action] = current_q + self.alpha * (target - current_q)


def train_sarsa(config: SarsaConfig, model_path: str) -> Dict[str, float]:
    logger = get_logger("sarsa_train")
    env = PygameBlackjackEnv(starting_budget=config.starting_budget, max_rounds=config.max_rounds)

    rng = np.random.default_rng(config.seed)
    agent = SarsaAgent(alpha=config.alpha, gamma=config.gamma, epsilon=config.epsilon, rng=rng)

    rewards = []
    epsilon = config.epsilon

    for episode in range(1, config.episodes + 1):
        state, info = env.reset(seed=config.seed + episode)
        action = agent.select_action(state, info["legal_actions"])

        done = False
        episode_reward = 0.0

        while not done:
            next_state, reward, terminated, truncated, next_info = env.step(action)
            done = terminated or truncated
            episode_reward += reward

            if done:
                agent.update(state, action, reward, next_state, 0, done=True)
                break

            next_action = agent.select_action(next_state, next_info["legal_actions"])
            agent.update(state, action, reward, next_state, next_action, done=False)
            state, action = next_state, next_action

        rewards.append(episode_reward)
        epsilon = max(config.epsilon_min, epsilon * config.epsilon_decay)
        agent.epsilon = epsilon

        if episode % 10_000 == 0:
            avg_reward = float(np.mean(rewards[-10_000:]))
            logger.info(
                f"[TRAIN] Episode {episode}/{config.episodes} | "
                f"eps={agent.epsilon:.4f} | avg_reward(last 10k)={avg_reward:.4f}"
            )

    os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(dict(agent.q_table), f)

    stats = {
        "episodes": float(config.episodes),
        "final_epsilon": float(agent.epsilon),
        "mean_reward": float(np.mean(rewards)),
        "positive_return_rate": float(np.mean(np.array(rewards) > 0)),
    }

    logger.info(f"[SAVE] model saved to {model_path}")
    logger.info(
        "[TRAIN DONE] "
        f"mean_reward={stats['mean_reward']:.4f}, positive_rate={stats['positive_return_rate']:.4f}, "
        f"final_epsilon={stats['final_epsilon']:.4f}"
    )

    return stats


def load_q_table(model_path: str) -> DefaultDict[State, np.ndarray]:
    with open(model_path, "rb") as f:
        raw_table = pickle.load(f)

    q_table: DefaultDict[State, np.ndarray] = defaultdict(
        lambda: np.zeros(ACTION_SPACE_SIZE, dtype=np.float64)
    )
    q_table.update(raw_table)
    return q_table


def evaluate_policy(
    model_path: str,
    episodes: int,
    seed: int,
    starting_budget: int,
    max_rounds: int,
) -> Dict[str, float]:
    logger = get_logger("sarsa_eval")
    env = PygameBlackjackEnv(starting_budget=starting_budget, max_rounds=max_rounds)
    q_table = load_q_table(model_path)
    rewards = []
    final_budgets = []
    strategy_observed_steps = 0
    strategy_followed_steps = 0

    for episode in range(episodes):
        state, info = env.reset(seed=seed + episode)
        done = False
        episode_reward = 0.0

        while not done:
            legal_actions = info["legal_actions"]
            action = _greedy_action_from_q_table(q_table, state, legal_actions)
            if env.state.game_state == "playing" and legal_actions:
                strategy_observed_steps += 1
                if action == env._recommended_strategy_action(legal_actions):
                    strategy_followed_steps += 1
            next_state, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            episode_reward += reward
            state = next_state

        rewards.append(episode_reward)
        final_budgets.append(info["budget"])

    rewards_arr = np.array(rewards)
    budget_arr = np.array(final_budgets)
    strategy_follow_rate = (
        float(strategy_followed_steps) / strategy_observed_steps
        if strategy_observed_steps
        else 0.0
    )
    results = {
        "episodes": float(episodes),
        "mean_reward": float(np.mean(rewards_arr)),
        "mean_final_budget": float(np.mean(budget_arr)),
        "broke_rate": float(np.mean(budget_arr < min(BET_AMOUNTS))),
        "strategy_follow_rate": strategy_follow_rate,
    }

    logger.info(
        "[EVAL] "
        f"episodes={episodes}, mean_reward={results['mean_reward']:.4f}, "
        f"mean_final_budget={results['mean_final_budget']:.2f}, broke_rate={results['broke_rate']:.4f}, "
        f"strategy_follow_rate={results['strategy_follow_rate']:.4f}"
    )
    return results


def _greedy_action_from_q_table(
    q_table: DefaultDict[State, np.ndarray],
    state: State,
    legal_actions: List[int],
) -> Action:
    if not legal_actions:
        return 0

    action = int(legal_actions[0])
    best_value = q_table[state][action]
    for candidate in legal_actions[1:]:
        candidate_value = q_table[state][candidate]
        if candidate_value > best_value:
            best_value = candidate_value
            action = int(candidate)
    return action


def play_policy_rendered(
    model_path: str,
    episodes: int,
    seed: int,
    starting_budget: int,
    max_rounds: int,
) -> Dict[str, float]:
    """Render policy rollouts in pygame and return evaluation-style metrics."""
    import pygame
    from blackjack_game import BlackjackGame

    logger = get_logger("sarsa_play")
    env = PygameBlackjackEnv(starting_budget=starting_budget, max_rounds=max_rounds)
    q_table = load_q_table(model_path)
    game = BlackjackGame()
    game.state.budget = starting_budget

    rewards: List[float] = []
    final_budgets: List[int] = []
    broke_count = 0

    def draw_eval_overlay(current_episode: int, completed_episodes: int, current_broke_count: int) -> None:
        panel_width = 220
        panel_height = 92
        panel_x = game.width - panel_width - 20
        panel_y = game.height - panel_height - 20

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 140))
        pygame.draw.rect(panel, (255, 255, 255, 180), (0, 0, panel_width, panel_height), 2, border_radius=10)

        title = game.renderer.font_small.render("Eval HUD", True, (255, 215, 0))
        episode = game.renderer.font_small.render(f"Episode: {current_episode}/{episodes}", True, (255, 255, 255))
        completed = game.renderer.font_small.render(f"Completed: {completed_episodes}", True, (255, 255, 255))
        broke = game.renderer.font_small.render(f"Broke: {current_broke_count}", True, (255, 215, 0))

        panel.blit(title, (12, 8))
        panel.blit(episode, (12, 30))
        panel.blit(completed, (12, 52))
        panel.blit(broke, (12, 74))
        game.screen.blit(panel, (panel_x, panel_y))
        pygame.display.update()

    for episode in range(episodes):
        state, info = env.reset(seed=seed + episode)
        done = False
        episode_reward = 0.0

        while not done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    logger.info("[PLAY] Window closed by user.")
                    rewards_arr = np.array(rewards if rewards else [0.0])
                    budget_arr = np.array(final_budgets if final_budgets else [starting_budget])
                    return {
                        "episodes": float(len(rewards)),
                        "mean_reward": float(np.mean(rewards_arr)),
                        "mean_final_budget": float(np.mean(budget_arr)),
                        "broke_rate": float(np.mean(budget_arr < min(BET_AMOUNTS))),
                    }

            game.state = env.state
            game.draw()
            draw_eval_overlay(episode + 1, episode, broke_count)
            game.clock.tick(6)

            action = _greedy_action_from_q_table(q_table, state, info["legal_actions"])
            next_state, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            episode_reward += reward
            state = next_state

        rewards.append(episode_reward)
        final_budget = info["budget"]
        final_budgets.append(final_budget)
        if final_budget < min(BET_AMOUNTS):
            broke_count += 1

    pygame.quit()

    rewards_arr = np.array(rewards)
    budget_arr = np.array(final_budgets)
    return {
        "episodes": float(episodes),
        "mean_reward": float(np.mean(rewards_arr)),
        "mean_final_budget": float(np.mean(budget_arr)),
        "broke_rate": float(np.mean(budget_arr < min(BET_AMOUNTS))),
    }


def _print_metrics(prefix: str, metrics: Dict[str, float]) -> None:
    line = (
        f"[{prefix}] episodes={int(metrics['episodes'])} "
        f"mean_reward={metrics['mean_reward']:.4f} "
        f"mean_final_budget={metrics['mean_final_budget']:.2f} "
        f"broke_rate={metrics['broke_rate']:.4f}"
    )
    if "strategy_follow_rate" in metrics:
        line += f" strategy_follow_rate={metrics['strategy_follow_rate']:.4f}"
    print(line)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train and evaluate a SARSA Blackjack agent")
    parser.add_argument("--mode", choices=["train", "eval", "play", "ui"], default="train")
    parser.add_argument("--no-log", action="store_true", help="Disable file logging for this run")
    parser.add_argument("--episodes", type=int, default=500_000, help="Training episodes")
    parser.add_argument("--eval-episodes", type=int, default=20_000, help="Evaluation episodes")
    parser.add_argument("--alpha", type=float, default=0.05, help="Learning rate")
    parser.add_argument("--gamma", type=float, default=0.99, help="Discount factor")
    parser.add_argument("--epsilon", type=float, default=1.0, help="Initial epsilon")
    parser.add_argument("--epsilon-min", type=float, default=0.05, help="Minimum epsilon")
    parser.add_argument("--epsilon-decay", type=float, default=0.999988, help="Per-episode epsilon decay")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--starting-budget", type=int, default=500)
    parser.add_argument("--max-rounds", type=int, default=50)
    parser.add_argument("--model-path", type=str, default=DEFAULT_MODEL_PATH)
    parser.add_argument(
        "--render",
        action="store_true",
        help="Open pygame window in play mode to visualize policy rollouts",
    )
    return parser


def run_from_args(args: argparse.Namespace) -> None:
    if args.mode == "train":
        config = SarsaConfig(
            episodes=args.episodes,
            alpha=args.alpha,
            gamma=args.gamma,
            epsilon=args.epsilon,
            epsilon_min=args.epsilon_min,
            epsilon_decay=args.epsilon_decay,
            eval_episodes=args.eval_episodes,
            seed=args.seed,
            starting_budget=args.starting_budget,
            max_rounds=args.max_rounds,
        )
        train_stats = train_sarsa(config, args.model_path)
        eval_stats = evaluate_policy(
            args.model_path,
            args.eval_episodes,
            seed=args.seed,
            starting_budget=args.starting_budget,
            max_rounds=args.max_rounds,
        )
        print(
            f"[TRAIN] episodes={int(train_stats['episodes'])} "
            f"mean_reward={train_stats['mean_reward']:.4f} "
            f"positive_rate={train_stats['positive_return_rate']:.4f} "
            f"final_epsilon={train_stats['final_epsilon']:.4f}"
        )
        _print_metrics("EVAL", eval_stats)
    elif args.mode in {"eval", "play"}:
        episodes = args.eval_episodes if args.mode == "eval" else max(1, min(200, args.eval_episodes))
        if args.mode == "play" and args.render:
            metrics = play_policy_rendered(
                model_path=args.model_path,
                episodes=episodes,
                seed=args.seed,
                starting_budget=args.starting_budget,
                max_rounds=args.max_rounds,
            )
            _print_metrics("PLAY", metrics)
        else:
            metrics = evaluate_policy(
                model_path=args.model_path,
                episodes=episodes,
                seed=args.seed,
                starting_budget=args.starting_budget,
                max_rounds=args.max_rounds,
            )
            _print_metrics("EVAL" if args.mode == "eval" else "PLAY", metrics)
