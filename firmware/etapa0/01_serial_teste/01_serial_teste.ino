/*
 * Etapa 0.1 — Teste Serial
 * Placa: ESP32-2432S028R
 *
 * Sucesso: no Monitor Serial (115200) aparece "Yellow OK" a cada segundo.
 */

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println();
  Serial.println("=================================");
  Serial.println(" Diário Estoico — Etapa 0.1");
  Serial.println(" ESP32-2432S028R Serial OK");
  Serial.println("=================================");
}

void loop() {
  Serial.println("Yellow OK");
  delay(1000);
}
