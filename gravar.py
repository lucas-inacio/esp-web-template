import gzip
import json
import os
import pathlib
import shutil
import subprocess
import sys
from io import StringIO
from os import path

ADDRESS_SPIFFS = "0x300000"
SKETCH_NAME = "esp8266"
TMP_FILE_NAME = "fs.out"
ARDUINO_CLI_COMMAND_CONFIG = "arduino-cli config dump --format json"
ARDUINO_CLI_COMMAND_COMPILE = "arduino-cli compile -b esp8266:esp8266:nodemcuv2:mmu=4816H,eesz=4M1M {Sketch}"
ARDUINO_CLI_COMMAND_UPLOAD = "arduino-cli upload -p {Port} -b esp8266:esp8266:nodemcuv2 {Sketch}"
MKSPIFFS_ARGS = " -c {Sketch}/data -p 256 -b 8192 -s 1048576 " + TMP_FILE_NAME
ESPTOOL_COMMAND_WRITE = "python -m esptool -p {Port} -b 115200 write_flash {Address} {File}"

def run_command(command_string):
    completedProcess = subprocess.run(command_string.split(), capture_output=True, shell=True)
    completedProcess.check_returncode()
    return completedProcess.stdout

def get_arduino_config():
    """
    Obtém as configurações de arduino-cli e as retorna um dicionário.
    A função tenta executar o programa arduino-cli que deve estar no
    caminho do sistema.

    Retorna:
    dict: Um dicionário contendo a configuração reportada por arduino-cli config dump --format json
    """
    try:
        output = run_command(ARDUINO_CLI_COMMAND_CONFIG)
        io = StringIO(output.decode('utf-8'))
        return json.load(io)
    except FileNotFoundError:
        raise FileNotFoundError('arduino-cli não encontrado')

def find_mkspiffs_bin(root_dir, recursive=False):
    """
    Retorna o caminho absoluto do executável mkspiffs.

    Parâmetros:
    root_dir (string): O diretório base por onde começar a procurar.
    recursive (bool): Uso interno para permitir a recursão da função.

    Retorna:
    string: O caminho absoluto do executável mkspiffs.
    """
    if not recursive:
        mkspiffs_dir = path.join(root_dir, 'packages/esp8266/tools/mkspiffs')
        mkspiffs_dir = path.abspath(path.normpath(mkspiffs_dir))

        if not path.isdir(mkspiffs_dir):
            raise FileNotFoundError('mkspiffs não encontrado')

        return find_mkspiffs_bin(mkspiffs_dir, True)
    else:
        for sub in os.scandir(root_dir):
            if sub.is_dir():
                return find_mkspiffs_bin(sub.path, True)
            elif sub.is_file() and sub.name.find('mkspiffs') >= 0:
                return sub.path
            else:
                raise FileNotFoundError('mkspiffs não encontrado')

def run_mkspiffs(mkspiffs_path):
    """
    Executa o programa mkspiffs como: 
    
    mkspiffs -c esp8266_firebase/data -p 256 -b 8192 -s 1048576 f.out
    """
    try:
        run_command(mkspiffs_path + MKSPIFFS_ARGS.format(Sketch=SKETCH_NAME))
    except subprocess.CalledProcessError:
        raise Exception('Erro ao criar sistema de arquivos com mkspiffs.')

def compress_files_in_dir(dir):
    for entry in pathlib.Path(dir).glob('**/*'):
        if entry.is_file() and entry.suffix != '.gz' and not entry.name.endswith('.LICENSE.txt'):
            with open(entry.absolute(), 'rb') as file_in:
                with gzip.open(str(entry.absolute()) + '.gz', 'wb') as file_out:
                    shutil.copyfileobj(file_in, file_out)

# Exclui arquivos não comprimidos
def exclude_files(parent, contents):
    root = pathlib.Path(parent)
    ignore = [x for x in contents if root.joinpath(x).is_file() and not x.endswith('.gz')]
    return ignore

def clean_up_temp_files():
    shutil.rmtree(pathlib.Path(SKETCH_NAME).joinpath('data'))
    shutil.rmtree('build')
    if path.isfile(TMP_FILE_NAME):
        os.remove(TMP_FILE_NAME)

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise Exception('Especifique a porta serial')

        # Cria arquivos estáticos do site (bundle)
        run_command('npm run build')
        # Comprime os arquivos no diretório resultante
        compress_files_in_dir('build')
        # Copia os arquivos comprimidos para o diretório esp8266/data
        shutil.copytree('build', 'esp8266/data', ignore=exclude_files, dirs_exist_ok=True)
        # Copia public index.htm para esp8266/data
        shutil.copyfile('public/index.htm', 'esp8266/data/index.htm')

        # Obtém diretório data do arduino-cli
        print('Obtendo configurações de arduino-cli...')
        config = get_arduino_config()

        # Encontra o executável de mkspiffs a partir do diretório data
        # e cria sistema de arquivos
        mkspiffs_path = find_mkspiffs_bin(config['directories']['data'])
        print('Econtrado mkspiffs em', mkspiffs_path)
        print('Criando sistema de arquivos spiffs...')
        run_mkspiffs(mkspiffs_path)

        # Compila sketch e grava no microcontrolador
        print('Compilando sketch...')
        run_command(ARDUINO_CLI_COMMAND_COMPILE.format(Sketch=SKETCH_NAME))

        # Usa esptool para gravar o arquivo gerado por mkspiffs no microcontrolador
        print('Gravando sistema de arquivos spiffs...')
        run_command(ESPTOOL_COMMAND_WRITE.format(Port=sys.argv[1], Address=ADDRESS_SPIFFS, File=TMP_FILE_NAME))

        # Grava o sketch no esp8266
        print('Gravando sketch...')
        run_command(ARDUINO_CLI_COMMAND_UPLOAD.format(Port=sys.argv[1], Sketch=SKETCH_NAME))
    except subprocess.CalledProcessError as e:
        print('Erro ao tentar executar arduino-cli. Código', e.returncode)
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(e)
    finally:
        clean_up_temp_files()
