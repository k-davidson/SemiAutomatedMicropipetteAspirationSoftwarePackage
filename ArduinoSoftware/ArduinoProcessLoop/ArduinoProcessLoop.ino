#define PUMP  LOW
#define DRAW  HIGH
#define STEPS 2048

#define motorSlowSpeed 3
#define motorFastSpeed 15
#define slowFlowRate 1
#define fastFlowRate 3

// Set for dir of step
bool STEP_STATE = false;
// Set when timer meets step thresh
bool STEP = false;
// Set if recieving serial communication
bool RECIEVING = false;
int resetCode = 0;

// Set difference in stepper/pump in steps
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

// Set the number of axis
int nAxis = 2;
// Tool selection
int tSel = 0;

// Stepper motor communication pins
int pulPin[] = {0, 0};
int dirPin[] = {0, 0};
int setPos[] = {0,0};
int currPos[] = {0,0};
int motorRate[] = {0,0};
// Time since previous stepper update
unsigned long prevUpdate[] = {0,0};

bool ABS = true;
int posCode = 0;

void setup() {
  // put your setup code here, to run once:
  // Initialise serial communication
  Serial.begin(57600);

  // Set Pump direction and pump operational trigger
  pinMode(directionPin, OUTPUT);
  digitalWrite(directionPin, HIGH);
  pinMode(pumpPin, OUTPUT);
  digitalWrite(pumpPin, HIGH);
  pinMode(activePumpPin, INPUT);

  // Initialise Timer 2 
  timer2Setup();

  // Initialise Stepper Motor pins
  pinMode(51, OUTPUT);
  pinMode(50, OUTPUT);

  pinMode(53, OUTPUT);
  pinMode(52, OUTPUT);
  
  digitalWrite(51, LOW);
  digitalWrite(50, LOW);
  
  digitalWrite(53, LOW);
  digitalWrite(52, LOW);

  // Set stepper 1 pins in pulse array/direction pin
  pulPin[1] = 51;
  dirPin[1] = 50;

  // Set stepper 2 pins in pulse array/direction pin
  pulPin[0] = 53;
  dirPin[0] = 52;

  // Initialise motor rate
  motorRate[1] = 1000;
  motorRate[0] = 1000;

  // Set time since previous update
  prevUpdate[1] = micros();
  prevUpdate[0] = micros();
}

void loop() {
  // put your main code here, to run repeatedly:
  // Initialise empty input array
  char fullInput[100] = "\0";
  // Check if pending serial communication
  if(Serial.available()) {
    Serial.readBytesUntil('\n', fullInput, 100);

    // Check if Syringe pump at max feed rate command
    if(sscanf(fullInput, "N%d S00 %d",&lNum, &desiredVolume) == 2) {
      Serial.print("ACK\n");
    }

    // Check if Syringe pump at set feed rate command
    else if(sscanf(fullInput, "N%d S01 %d",&lNum, &desiredVolume) == 2) {
      Serial.print("ACK\n");
    }

    // Check if Stepper motor positioning at set feed rate command
    else if(sscanf(fullInput, "N%d G00 %d %d", &lNum, setPos + tSel, motorRate + tSel) == 3) {
      Serial.print("ACK\n");
      
    }

    // Check if tool select command
    else if(sscanf(fullInput, "N%d T %d", &lNum, &tSel) == 2) {
      Serial.print("ACK\n");
    }

    // Check if changing between ABS/Relative coordinates
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
        }
        ABS = temp;

      }
    }

    // Check if reset command
    else if(sscanf(fullInput, "N%d # %d", &lNum, resetCode) == 2) {
      Serial.print("ACK\n");
      if(resetCode == 0) {
        for(int i = 0; i < 2; i++) {
          currPos[i] = 0;
          setPos[i] = 0;
        }
      }
    }

    // Check if start/end character 
    else if(sscanf(fullInput, "N%d %", &lNum) == 1) {
      Serial.print("ACK\n");
      RECIEVING = !RECIEVING;
    }
    
  }

  delay(50);

  // Check if difference between desired and actual volume
  if((currVolume - desiredVolume != 0) && (digitalRead(activePumpPin) != HIGH) && !RECIEVING) {
    // Check if require pumping
    if(currVolume < desiredVolume) {
      digitalWrite(directionPin, LOW);
      currVolume++;
    // Otherwise, withdrawing
    } else {
      digitalWrite(directionPin, HIGH);
      currVolume--;
    }

    // Step pump forward
    delay(50);
    stepPump();
    delay(250);
  }

  // If need to step motor and not currently recieving
  if(motorStep && !RECIEVING) {
    // Iterate over axis
    for(int i = 0; i < 2; i++) {
      // If difference between actual and desired position
      if((*(setPos + i) != *(currPos + i)) && (motorStep)) {
        stepMotor(i, (pow(10,6))/(*(motorRate + i)));
      }
    }
  }
}


void stepPump() {
  // Step pump operational trigger pin
  digitalWrite(pumpPin, HIGH);
  delay(100);
  digitalWrite(pumpPin, LOW);
}

void stepMotor(int tSel, int r) {
  // Get direction from difference in desired/actual position
  int dir = *(setPos + tSel) - *(currPos + tSel) > 0 ? 1 : -1;
  // Set direction pin
  digitalWrite(dirPin[tSel], dir > 0 ? LOW : HIGH);
  int state = digitalRead(pulPin[tSel]);
  // Iterate over position, until matching position
  while(*(currPos + tSel) != *(setPos + tSel)) {
    // Write to pulse pin
    digitalWrite(pulPin[tSel], !state);
    state = !state;
    delayMicroseconds(r);
    *(currPos + tSel) += dir;
  }
  
}


void timer2Setup() {
  // Initialise Timer 2 state
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
  // Interrupt call, set motor step
  motorStep = 1;
}
