#include <ESP8266WiFi.h>
#include <ESPAsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <FS.h>

#include <map>

#include "web_data.h"

#define SSID "SSID"
#define PASS "PASS"

String getMime(const char *str) {
    String url{ str };
    if (url.endsWith(".css")) {
        return F("text/css");
    } else if (url.endsWith(".js")) {
        return F("text/javascript");
    } else if (url.endsWith(".htm") || url.endsWith(".html")) {
        return F("text/html");
    } else {
        return "";
    }
}

bool ledState = false;
typedef void (*Handler)(AsyncWebServerRequest *);
std::map<String, Handler> requestMap{
    {
        "/toggle",
        [](AsyncWebServerRequest *request) {
            ledState = !ledState;
            digitalWrite(LED_BUILTIN, ledState);
            request->send(200);
        } 
    } 
};

void onNotFound(AsyncWebServerRequest *request)
{
    String url = request->url();
    if (request->method() == HTTP_GET) {
        if (url.indexOf(".") < 0) url = "/index.htm";
        String mime = getMime(url.c_str());
        int i = 0;
        for (; i < gzipDataCount; ++i) {
            if (strcmp(url.c_str(), gzipDataMap[i].path) == 0) {
                AsyncWebServerResponse *response = request->beginResponse_P(
                    200, mime.c_str(), gzipDataMap[i].data, gzipDataMap[i].dataSize);
                response->addHeader("Content-Encoding", "gzip");
                request->send(response);
                return;
            }
        }
    } else if (request->method() == HTTP_POST) {
        for (auto &handler : requestMap)
        {
            if (handler.first == url) {
                handler.second(request);
                return;
            }
        }
    }

    Serial.print("URL nao encontrada: ");
    Serial.println(url);
    request->send(404);
}

AsyncWebServer server(80);
void setup() {
    SPIFFS.begin();
    Serial.begin(115200);
    delay(200);

    pinMode(D4, OUTPUT);

    Serial.print("Inicializando...");
    WiFi.mode(WIFI_STA);
    WiFi.begin(SSID, PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    // Reconecta ao WiFi automaticamente
    WiFi.setAutoReconnect(true);
    WiFi.persistent(true);
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());

    // Configurando servidor HTTP
    server.serveStatic("/", SPIFFS, "/");
    server.onNotFound(onNotFound);
    server.begin();
}

void loop() {

}
