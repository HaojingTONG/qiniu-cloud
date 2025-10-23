# Voice-OS: Voice-Activated macOS Assistant

A modular, voice-activated OS assistant for macOS that uses LLM (Claude) for intent understanding and AppleScript for system control.

## Features

- **Voice/Text Input**: ASR placeholder (currently text input) with future support for speech recognition
- **LLM Intent Parsing**: Uses Anthropic Claude API to understand natural language commands
- **Rule-Based Fallback**: Automatic fallback to keyword-based rules when LLM fails
- **Strict Schema Validation**: All LLM outputs validated by Pydantic
- **macOS Integration**: Execute commands via AppleScript and shell
- **Safety First**: Dangerous commands require confirmation
- **Dry-Run Mode**: Test without executing commands
- **TTS Feedback**: Speaks results using macOS `say` command

## Supported Intents

1. **system_setting**: Adjust volume, brightness, etc.
2. **play_music**: Control music playback
3. **web_search**: Search the web (opens in Safari)
4. **write_note**: Create notes in Notes app
5. **control_app**: Open/control applications
6. **clarify**: Request clarification for ambiguous/unsafe commands

## Project Structure

```
voice-os/
├── app/
│   ├── main.py          # CLI entry point (Typer)
│   ├── config.py        # Configuration from .env
│   ├── schema.py        # Pydantic intent models
│   ├── planner.py       # LLM + rule-based orchestration
│   ├── llm.py           # Anthropic API client
│   ├── asr.py           # ASR placeholder (text input)
│   ├── tts.py           # macOS 'say' wrapper
│   ├── verbalizer.py    # Generate natural responses
│   ├── executor.py      # Execute intents on macOS
│   └── utils.py         # AppleScript helpers
├── executor/
│   └── macos/
│       ├── system.applescript   # Volume control
│       ├── safari.applescript   # Open URLs
│       └── notes.applescript    # Create notes
├── prompts/
│   ├── system.txt       # LLM system prompt
│   └── fewshot.jsonl    # Few-shot examples
├── tests/
│   ├── tasks.csv        # Test cases (30 utterances)
│   └── replay.py        # Accuracy evaluation script
├── .env.example         # Environment template
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Prerequisites

- macOS (tested on macOS 10.15+)
- Python 3.11+
- Anthropic API key

### 2. Installation

```bash
# Clone or navigate to project directory
cd voice-os

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your Anthropic API key
# ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 3. Run Examples

```bash
# Single command (with LLM)
python app/main.py --text "把音量调到30%"

# Dry-run mode (show what would be executed)
python app/main.py --text "搜索Python教程" --dry-run

# Rule-based only (no LLM, no API key needed)
python app/main.py --text "播放音乐" --no-llm

# Interactive loop mode
python app/main.py

# Run basic tests
python app/main.py test

# Run accuracy evaluation (rule-based)
python tests/replay.py

# Run accuracy evaluation (with LLM, requires API key)
python tests/replay.py --llm
```

## Example Inputs & Expected Results

### Example 1: Volume Control
```
Input:  "把音量调到30%"
Intent: system_setting
Slots:  {"setting": "volume", "value": 30}
Action: Executes system.applescript to set volume to 30%
Output: "设置已完成" (spoken via TTS)
```

### Example 2: Web Search
```
Input:  "搜索Python教程"
Intent: web_search
Slots:  {"query": "Python教程"}
Action: Opens Safari with Google search for "Python教程"
Output: "已打开搜索结果" (spoken via TTS)
```

### Example 3: Dangerous Command (requires confirmation)
```
Input:  "删除所有文件"
Intent: clarify
Confirm: true
Safety: {"risk": "high", "reason": "Destructive operation"}
Output: "您确定要执行「删除所有文件」吗？这可能有风险。" (asks for confirmation)
```

## CLI Options

```bash
python app/main.py [OPTIONS]

Options:
  --text, -t TEXT    Direct text input (skip ASR)
  --dry-run          Only show what would be executed
  --no-llm           Use rule-based only (no API calls)
  --loop, -l         Continuous listening mode
  --help             Show help message
```

## Development

### Adding New Intents

1. Update `IntentName` in `app/schema.py`
2. Add extraction logic in `app/planner.py` (rule-based)
3. Add execution logic in `app/executor.py`
4. Update prompts in `prompts/system.txt` and `prompts/fewshot.jsonl`
5. Add test cases in `tests/tasks.csv`

### Adding New AppleScripts

1. Create `.applescript` file in `executor/macos/`
2. Follow pattern: `on run argv ... end run`
3. Update `app/executor.py` to call the script

## Testing

```bash
# Test with provided CSV tasks (rule-based, ~70% accuracy expected)
python tests/replay.py

# Test with LLM (~90% accuracy expected)
python tests/replay.py --llm

# Add your own test cases
# Edit tests/tasks.csv and add rows:
# utterance,expected_intent,expected_slots
```

## Safety Features

- **Keyword Detection**: Dangerous keywords (delete, format, shutdown) trigger safety checks
- **Confirmation Required**: High-risk operations require explicit user confirmation
- **Dry-Run Mode**: Test commands without executing
- **Error Recovery**: Failed LLM calls automatically fall back to rule-based parsing

## Limitations & Future Work

- **ASR**: Currently uses text input; plan to integrate faster-whisper or macOS dictation
- **TTS**: Uses basic `say` command; could improve with better voice/speed control
- **Intents**: Currently 6 intents; can extend to more macOS automation
- **Multi-step**: No support yet for complex multi-step workflows
- **Context**: No conversation history or context tracking

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
- Copy `.env.example` to `.env` and add your API key
- Or use `--no-llm` flag to run without LLM

### AppleScript Permission Errors
- macOS may require accessibility permissions for certain operations
- Go to System Preferences > Security & Privacy > Accessibility
- Add Terminal or your Python executable

### TTS Not Working
- Ensure macOS `say` command is available: `say "test"`
- Check audio output is not muted

## License

MIT License - feel free to use and modify for your needs.

## Contributing

This is a learning project and starter template. Feel free to:
- Report issues
- Suggest improvements
- Add new intents/features
- Improve LLM prompts

---

Built with ❤️ for macOS automation enthusiasts.
