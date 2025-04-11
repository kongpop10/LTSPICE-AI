# LTspice AI Assistant

An AI-powered assistant to automate and enhance circuit simulations using LTspice. This project integrates Python scripting with Large Language Models (LLMs) to streamline the workflow of creating, running, and analyzing SPICE simulations.

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue.svg)](https://github.com/kongpop10/LTSPICE-AI)


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
│   └── __pycache__/           # Python cache files
└── saved_circuits/            # Storage for circuit files
```

---

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/kongpop10/LTSPICE-AI.git
cd LTSPICE-AI
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
pip install numpy scipy matplotlib pyltspice openai streamlit python-dotenv
```

4. **Configure Environment Variables**

Create a `.env` file in the project root with your API keys:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
# Add any other API keys as needed
```

The application uses these environment variables to authenticate with the LLM API services. You can obtain an OpenRouter API key by signing up at [OpenRouter](https://openrouter.ai/).

5. **Configure LTspice Path**

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

## Screenshots

### AI Response to Circuit Request
![AI Response to Circuit Request](Screenshot1.png)
*The LTspice AI Assistant generates a netlist based on your natural language description and provides an AI summary of the changes made.*

### Simulation Results Visualization
![Simulation Results Visualization](Screenshot2.png)
*After running a simulation, the assistant displays the results in an interactive plot where you can select variables and customize the view.*

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