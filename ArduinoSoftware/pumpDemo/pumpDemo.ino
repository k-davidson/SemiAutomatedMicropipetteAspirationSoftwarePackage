#define PUMP  LOW
#define DRAW  HIGH
#define STEPS 2048

#define motorSlowSpeed 3
#define motorFastSpeed 15
#define slowFlowRate 1
#define fastFlowRate 3

bool STEP_STATE = false;
bool STEP = false;

bool RECIEVING = false;

int resetCode = 0;

int pumpStep = 0;
int motorStep = 0;

int dir = 0;
int lNum = 0;


int pumpPin = 8; // Falling edge calls the pumping program
int directionPin = 9; // Rising edge = PUMPING, Falling edge = INFUSING
int activePumpPin = 10; //HIGH if pump currently in use
int currVolume = 0;
int desiredVolume = 0;
    
//general Variables
boolean stepper_state = 0;
int prescaler = 1; //default of prescaler of 1


int nAxis = 2;
int tSel = 0;

int pulPin[] = {0, 0};
int dirPin[] = {0, 0};
int setPos[] = {0,0};
int currPos[] = {0,0};
int motorRate[] = {0,0};
unsigned long prevUpdate[] = {0,0};


bool ABS = true;
int posCode = 0;

void setup() {
  // put your setup code here, to run once:
  
  Serial.begin(57600);
  pinMode(directionPin, OUTPUT);
  
  digitalWrite(directionPin, HIGH);
  pinMode(pumpPin, OUTPUT);
  digitalWrite(pumpPin, HIGH);
  
  pinMode(activePumpPin, INPUT);
  
  timer2Setup();

  pinMode(51, OUTPUT);
  pinMode(50, OUTPUT);

  pinMode(53, OUTPUT);
  pinMode(52, OUTPUT);
  
  digitalWrite(51, LOW);
  digitalWrite(50, LOW);
  
  digitalWrite(53, LOW);
  digitalWrite(52, LOW);
  
  pulPin[1] = 51;
  dirPin[1] = 50;

  pulPin[0] = 53;
  dirPin[0] = 52;

  motorRate[1] = 1000;
  motorRate[0] = 1000;

  prevUpdate[1] = micros();
  prevUpdate[0] = micros();
}

void loop() {
  // put your main code here, to run repeatedly:
  
  char fullInput[100] = "\0";
  if(Serial.available()) {
    Serial.readBytesUntil('\n', fullInput, 100);
  
    if(sscanf(fullInput, "N%d S00 %d",&lNum, &desiredVolume) == 2) {
      Serial.print("ACK\n");
    }

    else if(sscanf(fullInput, "N%d S01 %d",&lNum, &desiredVolume) == 2) {
      Serial.print("ACK\n");
    }

    else if(sscanf(fullInput, "N%d G00 %d %d", &lNum, setPos + tSel, motorRate + tSel) == 3) {
      Serial.print("ACK\n");
      
    }

    else if(sscanf(fullInput, "N%d T %d", &lNum, &tSel) == 2) {
      Serial.print("ACK\n");
    }

    else if(sscanf(fullInput, "N%d G%d", &lNum, &posCode) == 2) {
      Serial.print("ACK\n");

      if(posCode == 90) {
        ABS = true;
      } else if(posCode == 91) {
        ABS = false;
      }
      else if(posCode == 10) {
        bool temp = ABS;
        ABS = true;
        for(int i = 0; i < nAxis; i++) {
          
          *(setPos + i) = 0;
          //stepMotor(axisList[i], posSteps + i , axPos + i, 0);
        }
        ABS = temp;

      }
    }

    else if(sscanf(fullInput, "N%d # %d", &lNum, resetCode) == 2) {
      Serial.print("ACK\n");
      if(resetCode == 0) {
        for(int i = 0; i < 2; i++) {
          currPos[i] = 0;
          setPos[i] = 0;
        }
      }
    }

    
    else if(sscanf(fullInput, "N%d %", &lNum) == 1) {
      Serial.print("ACK\n");
      RECIEVING = !RECIEVING;
    }
    
  }

  delay(50);
  
  if((currVolume - desiredVolume != 0) && (digitalRead(activePumpPin) != HIGH) && !RECIEVING) {
    if(currVolume < desiredVolume) {
      digitalWrite(directionPin, LOW);
      currVolume++;
    } else {
      digitalWrite(directionPin, HIGH);
      currVolume--;
    }

    delay(50);
    stepPump();
    delay(250);
  }

  if(motorStep && !RECIEVING) {
    for(int i = 0; i < 2; i++) {
      if((*(setPos + i) != *(currPos + i)) && (motorStep)) {
        stepMotor(i, (pow(10,6))/(*(motorRate + i)));
      }
    }
  }
}


void stepPump() {
  digitalWrite(pumpPin, HIGH);
  delay(100);
  digitalWrite(pumpPin, LOW);
}

void stepMotor(int tSel, int r) {
  
  int dir = *(setPos + tSel) - *(currPos + tSel) > 0 ? 1 : -1;
  digitalWrite(dirPin[tSel], dir > 0 ? LOW : HIGH);
  int state = digitalRead(pulPin[tSel]);
  while(*(currPos + tSel) != *(setPos + tSel)) {
    digitalWrite(pulPin[tSel], !state);
    state = !state;
    delayMicroseconds(r);
    *(currPos + tSel) += dir;
  }
  
}


void timer2Setup() {
  noInterrupts(); 
  TCCR2A = 0;
  TCCR2B = 0;
  TCNT2  = 0;

  OCR2A = 255;// = (16*10^6) / (250*1024) - 1 (must be <256) (16*10^6) / (
  TCCR2A |= (1 << WGM21);
  TCCR2B |= (1 << CS22)|(1 << CS20);
  TIMSK2 |= (1 << OCIE2A);
  interrupts();
}

ISR(TIMER2_COMPA_vect) {
  motorStep = 1;
}
