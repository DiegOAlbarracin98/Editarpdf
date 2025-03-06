import subprocess
import os

def run_streamlit():
    #obtiene la ruta del script de streamlit
    script_path = os.path.join(os.path.dirname(__file__), "editarpdf.py")
    
    #ejecuta la aplicacion streamlit
    subprocess.run(["streamlit", "run", script_path])
    
if __name__ == "__main__":
    run_streamlit()