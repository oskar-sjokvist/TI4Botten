# TI4Botten - Discord Bot for Twilight Imperium 4th Edition

TI4Botten is a Discord bot written in Python that provides faction randomization, game management, and statistics tracking for Twilight Imperium 4th Edition. The bot uses SQLAlchemy ORM with SQLite for data persistence and discord.py for Discord integration.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Critical Requirements

### Python Version
**REQUIRED**: Python 3.13 or higher due to `audioop-lts` dependency. The project will NOT install on Python 3.12 or lower.

### Environment Setup
**NEVER CANCEL**: Dependency installation can take 10-15 minutes due to large packages like discord.py. Set timeout to 30+ minutes.

Bootstrap the development environment:
```bash
# Verify Python version (must be 3.13+)
python3 --version

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate     # On Windows

# Install dependencies - NEVER CANCEL, takes 10-15 minutes
pip install -r requirements.txt
```

**TIMEOUT WARNING**: If `pip install` appears to hang, wait at least 20 minutes before considering alternatives. Network timeouts are common with large packages.

### Discord Bot Token
Create a `.token` file in the project root containing your Discord bot token:
```bash
echo "YOUR_DISCORD_BOT_TOKEN_HERE" > .token
```
**SECURITY**: The `.token` file is gitignored. Never commit tokens to source control.

## Working Effectively

### Development Workflow
**ALWAYS** follow this sequence when making changes:
1. Activate virtual environment: `source venv/bin/activate`
2. Install/update dependencies if needed: `pip install -r requirements.txt`
3. Run linting: `flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics`
4. Run tests: `pytest` (takes 2-3 minutes)
5. Test bot manually if making Discord command changes

### Building and Testing
```bash
# Lint the code - NEVER CANCEL, takes 1-2 minutes
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Run all tests - NEVER CANCEL, takes 2-3 minutes  
pytest

# Run specific test modules
pytest tests/test_bot.py
pytest src/game/tests/test_factions.py
pytest src/game/tests/test_draftingmodes.py
```

### Running the Bot
```bash
# Ensure you have a valid .token file first
# Start the bot - will run indefinitely until Ctrl+C
python app.py
```

**VALIDATION**: The bot will log "Starting bot..." and connect to Discord. Test with `!hello` command in a Discord server where the bot is present.

## Manual Validation Requirements

### After Making Changes
**ALWAYS** test these scenarios after making code changes:

1. **Basic Bot Commands**:
   - `!hello` - Should respond with "Hello!"
   - `!factions 3` - Should return "Here are 3 random factions:" followed by faction list

2. **Database Operations**:
   - Run `python app.py` to ensure database tables are created
   - Check that `app.db` file is created in project root
   - Database creation takes 5-10 seconds on first run

3. **Game Logic**:
   - Test faction filtering by source (Base Game, Prophecy of Kings, etc.)
   - Test drafting modes if modifying game logic
   - Verify faction data loads from `src/game/data/ti4_factions.csv`

4. **Test Suite Validation**:
   - Run `pytest tests/test_bot.py` to test Discord integration
   - Run `pytest src/game/tests/` to test game logic
   - Full test suite completes in 2-3 minutes when dependencies are available

## Project Structure

**Project Size**: 37 Python files, ~3,000 lines of code total

### Key Directories
- `app.py` — Main entrypoint, loads Discord token and starts bot
- `src/bot.py` — Bot initialization, cog loading, database setup
- `src/game/` — Core game logic and commands
  - `commands.py` — Discord commands for game management
  - `factions.py` — Faction data loading and randomization
  - `model.py` — SQLAlchemy database models
  - `draftingmodes.py` — Different drafting implementations
  - `data/ti4_factions.csv` — Source faction data
  - `tests/` — Unit tests for game logic
- `src/achievements/` — Achievement system
- `src/betting/` — Betting functionality  
- `src/rating/` — Player rating system
- `src/misc/` — Miscellaneous bot commands
- `tests/` — Integration tests for Discord bot commands

### Database
- Uses SQLite (`app.db`) with SQLAlchemy ORM
- Tables auto-created on first run
- Models defined in `src/game/model.py` and other `model.py` files
- Database is gitignored

### CI/CD
- GitHub Actions workflow: `.github/workflows/python-app.yml`
- Runs on Python 3.13.5 with Ubuntu latest
- **CI Steps**: pip upgrade → install flake8/pytest → install requirements → lint → test
- Lints with flake8: critical errors (E9,F63,F7,F82) fail build, other errors are warnings
- **ALWAYS** run `flake8` and `pytest` locally before committing to avoid CI failures
- **Build time**: CI typically completes in 3-5 minutes

## Common Tasks

### Adding New Factions
1. Edit `src/game/data/ti4_factions.csv` (currently 58 factions + header)
2. Add new row: `Faction Name,Source,Description`
3. Test with `!factions` command
4. Sources include: "Base Game", "Prophecy of Kings", "Codex", "Discordant Stars"

### Adding New Discord Commands
1. Add command method to appropriate cog in `src/*/commands.py`
2. Use `@commands.command()` decorator
3. Add integration test in `tests/test_bot.py`
4. Test manually with Discord bot

### Database Schema Changes
1. Modify models in `src/*/model.py`
2. Delete `app.db` to recreate tables (dev environment only)
3. Test database creation with `python app.py`

## Frequent Command Outputs

### Repository Root
```
.github/          - GitHub workflows and configurations
.gitignore        - Git ignore patterns (.token, *.db, __pycache__)
Dockerfile        - Python 3.13-slim container definition
LICENSE           - Project license
README.md         - Basic project documentation
app.py            - Main application entrypoint
pyproject.toml    - Python project configuration (pytest settings)
requirements.txt  - Python dependencies (27 packages)
src/              - Source code
tests/            - Integration tests
```

### src/ Directory Structure
```
src/
├── __init__.py
├── bot.py              - Main bot class and setup
├── models.py           - Base database models
├── typing.py           - Custom type definitions
├── achievements/       - Achievement system
├── betting/           - Betting functionality
├── game/              - Core TI4 game logic
│   ├── commands.py    - Game-related Discord commands
│   ├── controller.py  - Game state management
│   ├── draftingmodes.py - Faction drafting implementations
│   ├── factions.py    - Faction data and logic
│   ├── gamelogic.py   - Core game mechanics
│   ├── model.py       - Game database models
│   ├── data/          - CSV data files
│   ├── tests/         - Unit tests
│   └── util/          - Utility scripts
├── misc/              - Miscellaneous commands
└── rating/            - Player rating system
```

## Known Issues and Workarounds

### Python 3.12 Compatibility
- **Issue**: `audioop-lts==0.2.2` requires Python 3.13+
- **Solution**: Use Python 3.13 or remove audioop-lts dependency
- **Workaround**: For development, comment out audioop-lts in requirements.txt

### Network Timeouts During Installation
- **Issue**: `pip install` may timeout on large packages (discord.py is 15MB+)
- **Solution**: Use longer timeouts: `pip install --timeout 600 -r requirements.txt`
- **Alternative**: Install packages individually: `pip install discord.py SQLAlchemy pytest`
- **If persistent**: Check network connectivity, try different package index

### Docker Build Time
- **Expected Time**: 5-10 minutes for initial build
- **NEVER CANCEL**: Set timeout to 20+ minutes for Docker builds
- **Build command**: `docker build -t ti4botten .`

### Virtual Environment Issues
- **Always activate**: `source venv/bin/activate` before any pip commands
- **Windows users**: Use `venv\Scripts\activate` instead
- **Verify activation**: Check that prompt shows `(venv)` prefix

## Validation Checklist

Before committing changes, ALWAYS verify:
- [ ] `python3 --version` shows 3.13+
- [ ] `source venv/bin/activate` activates virtual environment
- [ ] `pip install -r requirements.txt` completes without errors
- [ ] `flake8 .` runs without critical errors (E9, F63, F7, F82)
- [ ] `pytest` passes all tests
- [ ] Bot starts with `python app.py` (requires valid .token)
- [ ] Basic commands work: `!hello`, `!factions 3`
- [ ] Database file `app.db` is created
- [ ] No secrets committed to git