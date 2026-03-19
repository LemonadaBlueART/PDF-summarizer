# PDF-summarizer
Summarize PDFs efficiently with AI models

Ministral-3-3B-Instruct.gguf : https://drive.google.com/file/d/1j9GCFfY3D7DvzL6wgAl1ikEqznlOOkvk/view?usp=sharing

Meta-Llama-3.1-8B-Instruct.gguf : https://drive.google.com/file/d/1xwGq-wOcXkCYZwXB5E2ObzkEo6XMElvm/view?usp=sharing

gemma-3-12b-it-gguf : https://huggingface.co/unsloth/gemma-3-12b-it-GGUF?utm_source=chatgpt.com&show_file_info=gemma-3-12b-it-UD-Q5_K_XL.gguf

Obs.: All models must be in the same folder as the code.

< -------------------------------------------------- >
 pip install PyMuPDF PyQt5 reportlab llama-cpp-python
< -------------------------------------------------- >

Linux/Mac:
# 1. Create a virtual environment
python3 -m venv pdf_ai_env

# 2. Activate the virtual environment
source pdf_ai_env/bin/activate

# 3. Install required packages
pip install PyMuPDF PyQt5 reportlab llama-cpp-python

Windows (CMD):
:: 1. Create a virtual environment
python -m venv pdf_ai_env

:: 2. Activate the virtual environment
pdf_ai_env\Scripts\activate

:: 3. Install required packages
pip install PyMuPDF PyQt5 reportlab llama-cpp-python

Windows (PowerShell):
# 1. Create a virtual environment
python -m venv pdf_ai_env

# 2. Activate the virtual environment
.\pdf_ai_env\Scripts\Activate.ps1

# 3. Install required packages
pip install PyMuPDF PyQt5 reportlab llama-cpp-python

