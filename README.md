# esp-web-template
Esqueleto de projeto Web para ESP8266 (NodeMCU v3 Lolin)

## Estrutura do projeto
- O código fonte da página web está localizado no diretório src.
- O código fonte do ESP8266 está no diretório esp8266.
- Há uma implementação utilizando arrays na memória flash para armazenar as páginas web em esp8266_progmem.

## Dependências
O projeto assume que o arduino-cli está instalado e está no caminho do sistema. Também é necessário que a plataforma esp8266:esp8266 esteja instalada bem como as bibliotecas que o projeto utiliza.

Primeiramente certifique-se de que a url para o ESP8266 esteja instalada:
```shell
arduino-cli config add board_manager.additional_urls https://arduino.esp8266.com/stable/package_esp8266com_index.json
arduino-cli core update-index
```
Em seguida instale a plataforma e as bibliotecas:
```shell
arduino-cli core install esp8266:esp8266
arduino-cli lib install "Firebase ESP8266 Client"
arduino-cli config set library.enable_unsafe_install true
arduino-cli lib install --git-url https://github.com/me-no-dev/ESPAsyncWebServer.git
arduino-cli lib install --git-url https://github.com/me-no-dev/ESPAsyncTCP.git
arduino-cli config set library.enable_unsafe_install false
```

## Configuração
Clone o repositório e, na raíz do projeto, digite `git submodule update --init` e então `npm install`. É necessário ter o nodejs instalado.

## Uso
Um script python (versão 3) está incluso para automatizar os processos de criação do bundle web, compilação e gravação do sistema de arquivos SPIFFS e do firmware.

O script necessita da porta serial no qual o ESP8266 está conectado:
```shell
python gravar.py COM4
```
O comando acima gera o bundle para ser gravado no sistema de arquivos SPIFFS. O firmware é compilado e gravado no ESP8266.

Para gravar as páginas na memória flash como arrays utilize:
```shell
python gravar.py COM4 --progmem
```

O firmware padrão apenas comuta o estado do LED do ESP8266 por meio de uma requisição POST enviada pela interface web.