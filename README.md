# SARSA-black-jack
This repo contains code for SARSA Reinforcement Learning programming of a blackjack environment


## Installation

### Quick Setup (Recommended)
Run the setup script from root:
```bash
./setup_env.sh
```

### Manual Setup
In the root: 

```bash
python3 -m venv gym_env
source gym_env/bin/activate
pip install -r requirements.txt
```

** you may need to replace python3 with py or python , and pip with pip3 on Windows. 

## Usage

Run from the `src` directory.

Train SARSA agent:
```bash
python3 main.py --mode train --episodes 200000 --no-log
```

or for the default (500k episodes, takes a few minutes)
```bash
python3 src/main.py --mode train --no-log
```

Training prints train/eval summary metrics to terminal when complete.

Disable file logging for any run:
add the `--no-log` flag

Evaluate saved model:
```bash
python3 main.py --mode eval --model-path ../models/sarsa_blackjack_sarsa.pkl --eval-episodes 200000 --no-log
```

Render a short self-play run (so we can see what it does in real-time):
```bash
python3 main.py --mode play --model-path ../models/sarsa_blackjack_sarsa.pkl --eval-episodes 50 --render --no-log
```
`--mode play --render` opens a pygame window and visualizes the trained policy. Without `--render`, play runs headless and prints summary metrics only.


Run the existing pygame UI manually:
```bash
python3 main.py --mode ui
```

## Logging

All runtime logs are written to:
```bash
./logs/blackjack.log
```

