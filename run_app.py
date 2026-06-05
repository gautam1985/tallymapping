import os
import sys
import streamlit.web.cli as stcli
import altair # Extra backup to prevent common bundling errors

if __name__ == '__main__':
    # Find the folder where the script is actually running
    base_path = os.path.dirname(__file__)
    script_path = os.path.join(base_path, 'app.py')
    
    # Force Python to find dependencies locally in the bundled directory
    sys.path.append(base_path)
    
    sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false"]
    sys.exit(stcli.main())