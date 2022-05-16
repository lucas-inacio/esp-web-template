import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
from io import StringIO
from os import path

ADDRESS_SPIFFS = "0x300000"
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
        run_command(mkspiffs_path + MKSPIFFS_ARGS.format(Sketch=target))
    except subprocess.CalledProcessError:
        raise Exception('Erro ao criar sistema de arquivos com mkspiffs.')

# Exclui arquivos não comprimidos
def exclude_files(parent, contents):
    root = pathlib.Path(parent)
    ignore = [x for x in contents if root.joinpath(x).is_file() and not x.endswith('.gz')]
    return ignore

def clean_up_temp_files():
    data_path = pathlib.Path(target).joinpath('data')
    static_dir = data_path.joinpath('static')
    index_file = data_path.joinpath('index.htm.gz')
    if static_dir.is_dir():
        shutil.rmtree(static_dir)
    if index_file.is_file():
        index_file.unlink()
    shutil.rmtree('build', ignore_errors=True)
    if path.isfile('esp8266_progmem/web_data.h'):
        os.remove('esp8266_progmem/web_data.h')
    if path.isfile(TMP_FILE_NAME):
        os.remove(TMP_FILE_NAME)

def parse_setup():
    parser = argparse.ArgumentParser(description='Gera o projeto e grava no esp8266')
    parser.add_argument('port', help='a porta serial a ser utilizada')
    parser.add_argument(
        '--progmem',
        help='gera um cabeçalho em esp8266_progmem/web_data.h ao invés de utilizar SPIFFS (padrão: --no-progmem)',
        action=argparse.BooleanOptionalAction)
    return parser.parse_args()

if __name__ == '__main__':
    target = 'esp8266'
    try:
        args = parse_setup()
        if args.progmem:
            target = 'esp8266_progmem'

        # Cria arquivos estáticos do site (bundle)
        run_command('npm run build')
        # Remove *.LICENSE.txt
        license_files = pathlib.Path('build').glob('**/*.LICENSE.txt')
        for file in license_files:
            file.unlink()

        # Copia public/index.htm para build/index.htm
        shutil.copyfile('public/index.htm', 'build/index.htm')
        # Comprime os arquivos no diretório resultante
        if args.progmem:
            run_command('python gzip-c-array/compress.py build -c esp8266_progmem/web_data.h')
        else:
            # Gera o bundle
            run_command('python gzip-c-array/compress.py build')
            # Copia os arquivos comprimidos para o diretório esp8266/data
            shutil.copytree('build', 'esp8266/data', ignore=exclude_files, dirs_exist_ok=True)

        # Obtém diretório data do arduino-cli
        print('Obtendo configurações de arduino-cli...')
        config = get_arduino_config()

        # Encontra o executável de mkspiffs a partir do diretório data
        # e cria sistema de arquivos se o subdiretório data não estiver vazio
        mkspiffs_path = find_mkspiffs_bin(config['directories']['data'])
        data_path = pathlib.Path(target).joinpath('data')
        if data_path.is_dir() > 0:
            count = 0
            for i in data_path.glob('**/*'):
                if i.is_file():
                    count += 1
            # Há dados no subdiretório data. Devemos gerar um binário SPIFFS
            if count > 0:
                print('Econtrado mkspiffs em', mkspiffs_path)
                print('Criando sistema de arquivos spiffs...')
                run_mkspiffs(mkspiffs_path)

        # Compila sketch e grava no microcontrolador
        print('Compilando sketch...')
        run_command(ARDUINO_CLI_COMMAND_COMPILE.format(Sketch=target))

        if pathlib.Path(TMP_FILE_NAME).is_file():
            # Usa esptool para gravar o arquivo gerado por mkspiffs no microcontrolador
            print('Gravando sistema de arquivos spiffs...')
            run_command(ESPTOOL_COMMAND_WRITE.format(Port=args.port, Address=ADDRESS_SPIFFS, File=TMP_FILE_NAME))

        # Grava o sketch no esp8266
        print('Gravando sketch...')
        run_command(ARDUINO_CLI_COMMAND_UPLOAD.format(Port=args.port, Sketch=target))
    except argparse.ArgumentError as e:
        print('Argumentos incorretos')
    except subprocess.CalledProcessError as e:
        print('Erro ao tentar executar arduino-cli. Código', e.returncode)
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(e)
    finally:
        clean_up_temp_files()
