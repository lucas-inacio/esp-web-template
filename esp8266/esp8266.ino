#include <ESP8266WiFi.h>
#include <ESPAsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <FS.h>

#include <map>

#define SSID "SSID"
#define PASS "PASS"

bool ledState = false;
typedef void (*Handler)(AsyncWebServerRequest *);
std::map<String, Handler> requestMap{
    {
        "/toggle",
        [](AsyncWebServerRequest *request) {
            ledState = !ledState;
            digitalWrite(D4, ledState);
            request->send(200);
        } 
    } 
};

void onNotFound(AsyncWebServerRequest *request)
{
    if (request->method() == HTTP_POST)
    {
        for (auto &handler : requestMap)
        {
            if (handler.first == request->url())
                handler.second(request);
        }
    }

    Serial.print("URL nao encontrada: ");
    Serial.println(request->url());
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
