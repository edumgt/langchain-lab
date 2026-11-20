import sys
import types
from pathlib import Path

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def install_optional_langchain_stubs():
    """Provide lightweight stubs for heavy optional LangChain/RAG deps when running
    unit/API tests outside the full Docker container."""
    optional_modules = {
        "langchain_text_splitters": {"RecursiveCharacterTextSplitter": type("RecursiveCharacterTextSplitter", (), {})},
        "langchain_core": {},
        "langchain_core.prompts": {"ChatPromptTemplate": type("ChatPromptTemplate", (), {})},
        "langchain_core.documents": {"Document": type("Document", (), {})},
        "langchain_core.output_parsers": {"StrOutputParser": type("StrOutputParser", (), {})},
        "langchain_core.runnables": {"RunnablePassthrough": type("RunnablePassthrough", (), {})},
        "langchain_community": {},
        "langchain_community.vectorstores": {"Chroma": type("Chroma", (), {})},
        "langchain_community.document_loaders": {
            "PyPDFLoader": type("PyPDFLoader", (), {}),
            "TextLoader": type("TextLoader", (), {}),
        },
        "langchain_community.chat_models": {"ChatOllama": type("ChatOllama", (), {})},
        "langchain_community.embeddings": {"OllamaEmbeddings": type("OllamaEmbeddings", (), {})},
        "langchain_openai": {
            "ChatOpenAI": type("ChatOpenAI", (), {}),
            "OpenAIEmbeddings": type("OpenAIEmbeddings", (), {}),
        },
        "langchain_classic": {},
        "langchain_classic.chains": {},
        "langchain_classic.chains.query_constructor": {},
        "langchain_classic.chains.query_constructor.schema": {"AttributeInfo": type("AttributeInfo", (), {})},
        "langchain_classic.retrievers": {},
        "langchain_classic.retrievers.self_query": {},
        "langchain_classic.retrievers.self_query.base": {"SelfQueryRetriever": type("SelfQueryRetriever", (), {})},
        "langchain_community.vectorstores.faiss": {"FAISS": type("FAISS", (), {})},
        "langchain_community.retrievers": {"BM25Retriever": type("BM25Retriever", (), {})},
        "chromadb": {},
        "reportlab": {},
        "reportlab.lib": {},
        "reportlab.lib.pagesizes": {"A4": (595, 842)},
        "reportlab.lib.styles": {"getSampleStyleSheet": lambda: {}, "ParagraphStyle": type("ParagraphStyle", (), {})},
        "reportlab.lib.units": {"mm": 2.8346},
        "reportlab.lib.colors": {"HexColor": lambda x: x},
        "reportlab.pdfbase": {},
        "reportlab.pdfbase.pdfmetrics": {"registerFont": lambda *a, **kw: None},
        "reportlab.pdfbase.ttfonts": {"TTFont": type("TTFont", (), {})},
        "reportlab.platypus": {
            "SimpleDocTemplate": type("SimpleDocTemplate", (), {}),
            "Paragraph": type("Paragraph", (), {}),
            "Spacer": type("Spacer", (), {}),
            "Table": type("Table", (), {}),
            "TableStyle": type("TableStyle", (), {}),
            "PageBreak": type("PageBreak", (), {}),
        },
    }
    for mod_name, attrs in optional_modules.items():
        if mod_name in sys.modules:
            continue
        try:
            __import__(mod_name)
        except ImportError:
            mod = types.ModuleType(mod_name)
            for k, v in attrs.items():
                setattr(mod, k, v)
            sys.modules[mod_name] = mod
