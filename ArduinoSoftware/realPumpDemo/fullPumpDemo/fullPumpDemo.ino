
int DIR_STATE = HIGH;


void setup() {
  // put your setup code here, to run once:
  pinMode(8, OUTPUT);
  pinMode(9, OUTPUT);
  pinMode(10, INPUT);

  digitalWrite(8, HIGH);
  delay(100);
  digitalWrite(9, HIGH);
  delay(100);
  digitalWrite(9, LOW);
  delay(100);

}

void loop() {
  /*
  digitalWrite(9, DIR_STATE);
  delay(300);
  
  digitalWrite(8, HIGH);
  delay(100);
  digitalWrite(8, LOW);
  

  delay(500);
  
  if(DIR_STATE == HIGH) {
    DIR_STATE = LOW;
  } else {
    DIR_STATE = HIGH;
  }
  */
  


  while(digitalRead(10) == HIGH) {
    }
  delay(300);
  
  // put your main code here, to run repeatedly:

}

void start_pump() {
  
}
