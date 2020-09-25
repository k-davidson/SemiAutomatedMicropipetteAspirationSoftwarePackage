#include <math.h>
#include <Stepper.h>

#define PUMP  LOW
#define DRAW  HIGH
#define CLK_SPEED 16000000
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

int32_t volume = 0;
int nSteps = 0;

//pins used
int speedPin = 4; //step speed pin set to 4
int directionPin = 5; //direction pin set to 3
    
//general Variables
boolean stepper_state = 0;
int prescaler = 1; //default of prescaler of 1

//___________________________change pump charactersitics:_______________________________________
double desiredFlowRate = 1; //mL/s
double runDist = 0.015; //number of meters in each direction LIMIT of 0.09m
double syringeDiameter = 0.0267; //diameter in m
uint32_t compareValue = 0;
double step_freq = 0.0;

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
  pinMode(speedPin, OUTPUT);
  setMode(PUMP);
  flowRate(1);
  timer2Setup();

  pinMode(51, OUTPUT);
  pinMode(50, OUTPUT);

  pinMode(53, OUTPUT);
  pinMode(52, OUTPUT);
  
  digitalWrite(51, LOW);
  digitalWrite(50, LOW);
  
  digitalWrite(53, LOW);
  digitalWrite(52, LOW);
  
  pulPin[0] = 51;
  dirPin[0] = 50;

  pulPin[1] = 53;
  dirPin[1] = 52;

  motorRate[0] = 1000;
  motorRate[1] = 1000;

  prevUpdate[0] = micros();
  prevUpdate[1] = micros();
}

void loop() {
  // put your main code here, to run repeatedly:
  
  char fullInput[100] = "\0";
  if(Serial.available()) {
    Serial.readBytesUntil('\n', fullInput, 100);
  
    if(sscanf(fullInput, "N%d S00 D%d V%d",&lNum, &dir, &volume) == 3) {
      Serial.print("ACK\n");
      flowRate(slowFlowRate);
      flowVolume(dir);
    }

    else if(sscanf(fullInput, "N%d S01 D%d V%d",&lNum, &dir, &volume) == 3) {
      Serial.print("ACK\n");
      flowRate(fastFlowRate);
      flowVolume(dir);
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
  
  if((volume > 0) && pumpStep && !RECIEVING) {
    pumpStep = 0;
    volume--;
    stepPump();
  }

  if(motorStep && !RECIEVING) {
    for(int i = 0; i < 2; i++) {
      if((*(setPos + i) != *(currPos + i)) && (motorStep)) {
        stepMotor(i, 1);
      }
    }
  }
  /*
  if(!RECIEVING) {
    for(int i = 0; i < 2; i++) {
       if(*(setPos + i) != *(currPos + i)) {
          if(micros() < *(prevUpdate + i)) {
            *(prevUpdate + i) = 0;
          }
          //motorRate steps/second therefore seconds/step = 1/motorRate
          if((1*10^6)/(*(motorRate + i)) < micros() - *(prevUpdate + i)) {
            *(prevUpdate + i) = micros();
            int dir = *(setPos + i) > *(currPos + i) ? 1 : -1;
            newStepMotor(i, dir);
            *(currPos + i) += dir;
       
          }
        }
    }
    motorStep = 0;
  }
  */
 
}

void flowVolume(int dir) {
  setMode(dir);
  volume = abs(volume);
  volume = (uint32_t)(volume/((3.14159*pow((syringeDiameter/2),2)*(0.00455/3200)*1000000)));
}



void flowRate(double df) {
  step_freq = df/(3.14159*pow((syringeDiameter/2),2)*(0.00455/3200)*1000000); //hz (number of steps in a second)
  compareValue = ((1/step_freq) * 16000000)-1; //interrupt compare value
  if(step_freq < (16000000/(65534*64))){ //change the clock prescaler to avoid overflow in OCRnA register
    compareValue = ((1/step_freq) * (16000000/256))-1;
    compareValue /= 2;
    prescaler = 256;
  } else if(step_freq < (16000000/(65534*8))){ 
    compareValue = ((1/step_freq) * (16000000/64))-1;
    compareValue /= 2;
    prescaler = 64;
  } else if(step_freq < (16000000/65534)){ 
    compareValue = ((1/step_freq) * (16000000/8))-1;
    compareValue /= 2;
    prescaler = 8;
  }
  timer1Setup(); 
}

void stepPump() {
  digitalWrite(speedPin, STEP_STATE);
  STEP_STATE = !STEP_STATE;
}


void setMode(int mode) {
  digitalWrite(directionPin, mode);
}

void newStepMotor(int tSel, int dir) {
  digitalWrite(dirPin[tSel], dir < 0 ? HIGH : LOW);
  int state = digitalRead(pulPin[tSel]);
  digitalWrite(pulPin[tSel], !state);
}

void stepMotor(int tSel, int r) {
  
  int dir = *(setPos + tSel) - *(currPos + tSel) > 0 ? 1 : -1;
  digitalWrite(dirPin[tSel], dir > 0 ? LOW : HIGH);
  int pause = r == 1 ? 300 : 3000;
  int state = digitalRead(pulPin[tSel]);
  while(*(currPos + tSel) != *(setPos + tSel)) {
    digitalWrite(pulPin[tSel], !state);
    state = !state;
    delayMicroseconds(300);
    *(currPos + tSel) += dir;
  }
  /*
  int cmp = ABS ? *p : 0;
  int d = *s - cmp > 0 ? 1 : -1;
  int pause = r ? 50 : 250;
  
  char debugStr[50];
  sprintf(debugStr, "cmp: %d, d: %d, s: %d\n", cmp, d, (*s));
  Serial.println(debugStr);
  
  
  int state = HIGH;
  while(0 < abs(*s-cmp)) {
    digitalWrite(pin, state);
    state = !state;
    delay(r);
    (*s) -= d;
    (*p) += d;
  }
  */
  
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

void timer1Setup(){
  noInterrupts(); 
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;

  //Value that the system counts to get desired frequency
  OCR1A = compareValue; 
  //CTC
  TCCR1B |= (1 << WGM12);
  //set the prescaler according to early checks
  if(prescaler == 1){
    //Prescaler 1
    TCCR1B |= (1 << CS10);
  } else if(prescaler == 8){
    //prescaler 8
    TCCR1B |= (1 << CS11);
  } else if(prescaler == 64){
    //prescaler 64
    TCCR1B |= (1 << CS11)|(1 << CS10);
  } else if(prescaler == 256){
    //prescaler 256
    TCCR1B |= (1 << CS12);
  }  
  //Output compare Match interrupt enable
  TIMSK1 |= (1 << OCIE1A);
  interrupts();
}

ISR(TIMER1_COMPA_vect){
  pumpStep = 1;
}

ISR(TIMER2_COMPA_vect) {
  motorStep = 1;
}
