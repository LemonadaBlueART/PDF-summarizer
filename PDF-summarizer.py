import sys
import fitz  # PyMuPDF, usado para ler PDFs
import os
import subprocess

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QProgressBar,
    QComboBox, QFrame, QMessageBox, QTextEdit, QSlider
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtMultimedia import QSound

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

from llama_cpp import Llama  # LLM local

# ===== CONFIG =====
# Caminhos dos modelos para cada nível
MODELOS_NIVEIS = {
    "Nível 1": "/home/asm/Downloads/qwen2.5-3b-instruct.gguf",
    "Nível 2": "/home/asm/Downloads/Meta-Llama-3.1-8B-Instruct.gguf",
    "Nível 3": "/home/asm/Downloads/gemma-3-12b.gguf"
}

# Valores padrão
DEFAULT_THREADS = 2
DEFAULT_DEVICE = "cpu"
DEFAULT_CONTEXT = 4096

# Inicializa o dict de LLMS (será carregado dinamicamente ao processar)
LLMS = {nivel: None for nivel in MODELOS_NIVEIS.keys()}

# ===== FUNÇÕES =====

def extrair_texto_pdf(caminho):
    """Extrai todo o texto de um PDF, limita a 100 páginas"""
    doc = fitz.open(caminho)
    if len(doc) > 100:
        raise ValueError("Limite de 100 páginas por pedido.")
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    return texto

def dividir_texto(texto, tamanho=2000):
    """Divide texto em chunks sem cortar palavras no meio"""
    chunks = []
    while len(texto) > tamanho:
        corte = texto.rfind(" ", 0, tamanho)
        if corte == -1:
            corte = tamanho
        chunks.append(texto[:corte])
        texto = texto[corte:].strip()
    if texto:
        chunks.append(texto)
    return chunks

def processar_chunk(chunk, idioma, llm):
    """Envia um chunk para o LLM e retorna resumo"""
    if not llm:
        raise ValueError("Modelo não carregado corretamente.")
    messages = [
        {"role": "system", "content": f"Você é um assistente especialista em resumos. Resuma o texto e destaque os pontos críticos em lista. Responda APENAS em {idioma}."},
        {"role": "user", "content": chunk}
    ]
    resposta = llm.create_chat_completion(
        messages=messages,
        max_tokens=2048,
        temperature=0.1
    )
    return resposta["choices"][0]["message"]["content"]

def gerar_pdf(conteudo, caminho_saida="resumo.pdf"):
    """Gera PDF do resumo"""
    doc = SimpleDocTemplate(caminho_saida, pagesize=letter)
    estilos = getSampleStyleSheet()
    estilo_normal = estilos["Normal"]
    story = []
    for paragrafo in conteudo.split("\n"):
        if paragrafo.strip():
            texto_formatado = paragrafo.replace('\n', '<br/>')
            story.append(Paragraph(texto_formatado, estilo_normal))
            story.append(Spacer(1, 6))
    doc.build(story)
    return caminho_saida

def abrir_pdf(caminho):
    """Abre PDF no visualizador padrão"""
    if sys.platform == "win32":
        os.startfile(caminho)
    elif sys.platform == "darwin":
        subprocess.run(["open", caminho])
    else:
        subprocess.run(["xdg-open", caminho])

# ===== THREAD =====
class Worker(QThread):
    """Thread para processar PDF sem travar a interface"""
    progresso = pyqtSignal(int)
    concluido = pyqtSignal(str)
    erro = pyqtSignal(str)

    def __init__(self, caminho_pdf, idioma, llm):
        super().__init__()
        self.caminho_pdf = caminho_pdf
        self.idioma = idioma
        self.llm = llm

    def run(self):
        try:
            texto = extrair_texto_pdf(self.caminho_pdf)
            if not texto.strip():
                self.erro.emit("O PDF não contém texto extraível (imagem escaneada?).")
                return

            chunks = dividir_texto(texto)
            resultado_final = ""
            total = len(chunks)

            for i, chunk in enumerate(chunks):
                resultado = processar_chunk(chunk, self.idioma, self.llm)
                resultado_final += resultado + "\n\n"
                progresso = int((i + 1) / total * 100)
                self.progresso.emit(progresso)

            caminho = gerar_pdf(resultado_final)
            self.concluido.emit(caminho)
        except Exception as e:
            self.erro.emit(str(e))

# ===== UI =====
class Janela(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Modifier")
        self.setGeometry(300, 300, 900, 600)
        self.setup_dark_theme()
        self.processando = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ===== LADO ESQUERDO =====
        esquerda = QVBoxLayout()
        esquerda.setSpacing(15)

        # Área de drop
        self.drop_area = QFrame()
        self.drop_area.setFrameShape(QFrame.StyledPanel)
        self.drop_area.setFixedHeight(150)
        self.drop_area.setStyleSheet("""
            QFrame { border: 2px dashed #555; border-radius: 10px; background-color: #2a2a2a; }
            QFrame:hover { border-color: #888; background-color: #333; }
        """)
        drop_layout = QVBoxLayout(self.drop_area)
        self.label = QLabel("Arraste um PDF aqui\nou clique no botão abaixo\n(Limite de 100 páginas por pedido)")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 16px; color: #ccc;")
        drop_layout.addWidget(self.label)
        esquerda.addWidget(self.drop_area)

        # Botão selecionar PDF
        self.botao = QPushButton("Selecionar PDF")
        self.botao.setCursor(Qt.PointingHandCursor)
        self.botao.setFixedHeight(40)
        self.botao.setStyleSheet("""
            QPushButton { background-color: #3c3c3c; border: 1px solid #555; border-radius: 5px; color: white; font-size: 16px; padding: 5px; }
            QPushButton:hover { background-color: #4a4a4a; border-color: #777; }
            QPushButton:pressed { background-color: #2a2a2a; }
            QPushButton:disabled { background-color: #222; color: #777; }
        """)
        self.botao.clicked.connect(self.abrir_arquivo)
        esquerda.addWidget(self.botao)

        # Combo idioma
        self.combo_idioma = QComboBox()
        self.combo_idioma.addItems(["Português", "Inglês"])
        self.combo_idioma.setFixedHeight(35)
        self.combo_idioma.setStyleSheet("""
            QComboBox { background-color: #2a2a2a; border: 1px solid #555; border-radius: 5px; color: white; padding: 5px; font-size: 14px; }
            QComboBox:hover { border-color: #777; }
        """)
        esquerda.addWidget(QLabel("Idioma:"))
        esquerda.addWidget(self.combo_idioma)

        # Combo nível
        self.combo_nivel = QComboBox()
        self.combo_nivel.addItems(list(MODELOS_NIVEIS.keys()))
        self.combo_nivel.setFixedHeight(35)
        self.combo_nivel.setStyleSheet("""
            QComboBox { background-color: #2a2a2a; border: 1px solid #555; border-radius: 5px; color: white; padding: 5px; font-size: 14px; }
            QComboBox:hover { border-color: #777; }
        """)
        esquerda.addWidget(QLabel("Nível do modelo:"))
        esquerda.addWidget(self.combo_nivel)

        # ===== NOVOS CONTROLES =====
        # Device
        self.combo_device = QComboBox()
        self.combo_device.addItems(["cpu", "cuda"])
        self.combo_device.setFixedHeight(35)
        self.combo_device.setStyleSheet("QComboBox { background-color: #2a2a2a; color: white; }")
        esquerda.addWidget(QLabel("Device:"))
        esquerda.addWidget(self.combo_device)

        # Threads
        self.combo_threads = QComboBox()
        self.combo_threads.addItems([str(i) for i in range(1, os.cpu_count() + 1)])
        self.combo_threads.setFixedHeight(35)
        self.combo_threads.setStyleSheet("QComboBox { background-color: #2a2a2a; color: white; }")
        esquerda.addWidget(QLabel("Threads:"))
        esquerda.addWidget(self.combo_threads)

        # Slider contexto
        self.slider_context = QSlider(Qt.Horizontal)
        self.slider_context.setMinimum(512)
        self.slider_context.setMaximum(16384)
        self.slider_context.setValue(DEFAULT_CONTEXT)
        self.slider_context.setTickInterval(512)
        self.slider_context.setTickPosition(QSlider.TicksBelow)
        self.slider_context.setStyleSheet("""
            QSlider::handle { background: #5a5a5a; width: 15px; }
            QSlider::groove:horizontal { background: #2a2a2a; height: 8px; }
        """)
        esquerda.addWidget(QLabel("Context size (n_ctx):"))
        esquerda.addWidget(self.slider_context)

        # Barra de progresso
        self.progress = QProgressBar()
        self.progress.setFixedHeight(20)
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #555; border-radius: 5px; background-color: #2a2a2a; color: white; text-align: center; }
            QProgressBar::chunk { background-color: #5a5a5a; border-radius: 5px; }
        """)
        esquerda.addWidget(self.progress)

        # Status
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size: 14px; color: #aaa;")
        esquerda.addWidget(self.status)

        main_layout.addLayout(esquerda, 2)

        # ===== LADO DIREITO =====
        direita = QVBoxLayout()
        direita.setSpacing(10)
        direita.addWidget(QLabel("Modelos carregados:"))
        self.lista_modelos = QTextEdit()
        self.lista_modelos.setReadOnly(True)
        self.lista_modelos.setStyleSheet("""
            QTextEdit { background-color: #1f1f1f; color: #fff; border: 1px solid #555; border-radius: 5px; }
        """)
        modelos_texto = "\n".join([f"{nivel}: {caminho}" for nivel, caminho in MODELOS_NIVEIS.items()])
        self.lista_modelos.setText(modelos_texto)
        direita.addWidget(self.lista_modelos)
        main_layout.addLayout(direita, 1)

        self.setAcceptDrops(True)

    # ===== MÉTODOS =====
    def setup_dark_theme(self):
        QApplication.setStyle('Fusion')
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        QApplication.setPalette(palette)

    def abrir_arquivo(self):
        if self.processando: return
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecionar PDF", "", "PDF Files (*.pdf)")
        if caminho:
            self.processar(caminho)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not self.processando:
            event.accept()
            self.drop_area.setStyleSheet("QFrame { border: 2px dashed #aaa; background-color: #3a3a3a; }")

    def dragLeaveEvent(self, event):
        if not self.processando:
            self.drop_area.setStyleSheet("QFrame { border: 2px dashed #555; background-color: #2a2a2a; }")

    def dropEvent(self, event):
        if self.processando: return
        self.drop_area.setStyleSheet("QFrame { border: 2px dashed #555; background-color: #2a2a2a; }")
        caminho = event.mimeData().urls()[0].toLocalFile()
        if caminho.lower().endswith(".pdf"):
            self.processar(caminho)
        else:
            self.mostrar_erro("Por favor, solte apenas arquivos PDF.")

    def processar(self, caminho):
        """Carrega modelo com configurações da UI e inicia thread"""
        nivel = self.combo_nivel.currentText()
        device = self.combo_device.currentText()
        threads = int(self.combo_threads.currentText())
        n_ctx = self.slider_context.value()

        caminho_modelo = MODELOS_NIVEIS.get(nivel)

        # Carrega LLM dinamicamente
        try:
            llm = Llama(
                model_path=caminho_modelo,
                n_ctx=n_ctx,
                n_threads=threads,
                n_batch=2,
                verbose=False,
                # device=device  # habilite se seu build suportar
            )
            LLMS[nivel] = llm
        except Exception as e:
            self.mostrar_erro(f"Não foi possível carregar {nivel}:\n{e}")
            return

        self.processando = True
        self.botao.setEnabled(False)
        self.combo_idioma.setEnabled(False)
        self.combo_nivel.setEnabled(False)
        self.combo_device.setEnabled(False)
        self.combo_threads.setEnabled(False)
        self.slider_context.setEnabled(False)

        idioma = self.combo_idioma.currentText()
        self.status.setText("Processando...")
        self.status.setStyleSheet("color: #aaa;")
        self.progress.setValue(0)

        self.worker = Worker(caminho, idioma, llm)
        self.worker.progresso.connect(self.progress.setValue)
        self.worker.concluido.connect(self.finalizado)
        self.worker.erro.connect(self.mostrar_erro)
        self.worker.start()

    def mostrar_erro(self, mensagem):
        self.status.setText("Erro durante o processamento!")
        self.status.setStyleSheet("color: #ff6666;")
        self.restaurar_interface()
        QMessageBox.critical(self, "Erro", mensagem)

    def finalizado(self, caminho):
        self.status.setText("Concluído!")
        self.status.setStyleSheet("color: #8bc34a;")
        self.restaurar_interface()
        QSound.play("plim.wav")
        abrir_pdf(caminho)

    def restaurar_interface(self):
        self.processando = False
        self.botao.setEnabled(True)
        self.combo_idioma.setEnabled(True)
        self.combo_nivel.setEnabled(True)
        self.combo_device.setEnabled(True)
        self.combo_threads.setEnabled(True)
        self.slider_context.setEnabled(True)

# ===== MAIN =====
if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = Janela()
    janela.show()
    sys.exit(app.exec_())