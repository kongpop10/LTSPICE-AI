# LTspice AI Assistant

An AI-powered assistant to automate and enhance circuit simulations using LTspice. This project integrates Python scripting with Large Language Models (LLMs) to streamline the workflow of creating, running, and analyzing SPICE simulations.

---

## Features

- **Automate LTspice Simulations**: Run LTspice simulations programmatically from Python.
- **Parse Simulation Results**: Extract and analyze waveform data from LTspice `.raw` files.
- **LLM Integration**: Use language models to generate SPICE netlists, analyze results, or assist with design.
- **Manage Settings**: Save and load user preferences for simulation workflows.
- **Interactive Interface**: Command-line or script-driven interaction for flexible usage.

---

## Project Structure

```
project-root/
├── ltspice-ai-assistant/
│   ├── app.py                 # Main entry point
│   ├── config.py              # Configuration management
│   ├── file_utils.py          # File handling utilities
│   ├── llm_interface.py       # Integration with language models
│   ├── ltspice_runner.py      # LTspice automation logic
│   ├── lt_icon.ico            # Application icon
│   ├── lt_icon.png            # Application icon (PNG format)
│   ├── prompts.py             # Prompt templates for LLMs
│   ├── raw_parser.py          # Parsing LTspice .raw files
│   ├── settings.json          # User configuration file
│   ├── settings_manager.py    # User settings management
│   ├── saved_circuits/        # Example or saved circuit files
│   ├── test_dir/              # Test directory
│   └── __pycache__/           # Python cache files
├── instructions/              # Project documentation and planning
└── saved_circuits/            # Storage for user circuit files
```

---

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/ltspice-ai-assistant.git
cd ltspice-ai-assistant
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
venv\Scripts\activate   # On Windows
# or
source venv/bin/activate  # On Linux/macOS
```

3. **Install dependencies**

```bash
pip install numpy scipy matplotlib pyltspice openai streamlit
```

4. **Configure LTspice Path**

Ensure LTspice is installed on your system. Update the path in the settings (`settings.json`) or via the assistant interface.

---

## Usage

Run the main application:

```bash
python ltspice-ai-assistant/app.py
```

Or if using Streamlit interface:

```bash
streamlit run ltspice-ai-assistant/app.py
```

Follow the prompts or integrate the modules into your own Python scripts.

---

## Documentation

See the `instructions/` directory for detailed documentation on project phases, design decisions, and usage examples:

- `Plan.md`
- `PyLTSPICE.md`
- `phase0.md` through `phase5.md`

---

## Dependencies

- Python 3.8+
- [LTspice](https://www.analog.com/en/design-center/design-tools-and-calculators/ltspice-simulator.html)
- [PyLTSpice](https://github.com/PyLTSpice/PyLTSpice)
- numpy, scipy, matplotlib
- openai (for LLM integration)
- streamlit (for web interface)

---

## License

MIT

---

## Acknowledgments

- Analog Devices for LTspice.
- The PyLTSpice community.
- OpenAI for LLM integration.