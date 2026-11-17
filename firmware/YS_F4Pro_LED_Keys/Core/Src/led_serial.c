#include "main.h"
#include "led_serial.h"
#include "led_app.h"
#include <stdio.h>
#include <string.h>

static UART_HandleTypeDef uart;
static uint8_t byte;
static volatile uint16_t head,tail;
static volatile uint8_t overflow;
static char ring[256];
static void send(const char *s){HAL_UART_Transmit(&uart,(const uint8_t *)s,(uint16_t)strlen(s),100);}
static void status(void){
    char out[128];
    snprintf(out,sizeof(out),"LEDSTATE MODE=%s RUN=%u DIR=%d MS=%lu MASK=%u KEYS=%lu CYCLES=%lu DONE=%lu\r\n",g_manual?"MANUAL":"FLOW",!g_manual&&!g_paused,g_direction,(unsigned long)g_interval_ms,LED_App_Mask(),(unsigned long)g_key_events,(unsigned long)g_cycles,(unsigned long)(g_flow_steps/3U));send(out);
}
void LED_Serial_Init(void){
    __HAL_RCC_GPIOB_CLK_ENABLE();__HAL_RCC_USART1_CLK_ENABLE();
    GPIO_InitTypeDef g={0};g.Pin=GPIO_PIN_6|GPIO_PIN_7;g.Mode=GPIO_MODE_AF_PP;g.Pull=GPIO_PULLUP;g.Speed=GPIO_SPEED_FREQ_HIGH;g.Alternate=GPIO_AF7_USART1;HAL_GPIO_Init(GPIOB,&g);
    uart.Instance=USART1;uart.Init.BaudRate=115200;uart.Init.WordLength=UART_WORDLENGTH_8B;uart.Init.StopBits=UART_STOPBITS_1;uart.Init.Parity=UART_PARITY_NONE;uart.Init.Mode=UART_MODE_TX_RX;uart.Init.HwFlowCtl=UART_HWCONTROL_NONE;uart.Init.OverSampling=UART_OVERSAMPLING_16;
    if(HAL_UART_Init(&uart)!=HAL_OK)Error_Handler();
    HAL_NVIC_SetPriority(USART1_IRQn,3,0);HAL_NVIC_EnableIRQ(USART1_IRQn);
    if(HAL_UART_Receive_IT(&uart,&byte,1)!=HAL_OK)Error_Handler();
    send("YS_F4Pro_LED READY PROTO=1\r\n");
}
void USART1_IRQHandler(void){HAL_UART_IRQHandler(&uart);}
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *h){
    if(h->Instance!=USART1)return;
    uint16_t next=(head+1)&255;
    if(next==tail)overflow=1;else{ring[head]=(char)byte;__DMB();head=next;}
    HAL_UART_Receive_IT(h,&byte,1);
}
void HAL_UART_ErrorCallback(UART_HandleTypeDef *h){
    if(h->Instance==USART1){overflow=1;HAL_UART_AbortReceive_IT(h);HAL_UART_Receive_IT(h,&byte,1);}
}
void LED_Serial_Poll(void){
    static char line[80];static unsigned len;static uint8_t discard;
    if(overflow){__disable_irq();tail=head;overflow=0;__enable_irq();len=0;discard=1;}
    while(tail!=head){char c=ring[tail];tail=(tail+1)&255;
        if(c=='\r')continue;
        if(c=='\n'){
            if(discard)send("ERR LINE\r\n");
            else if(len){line[len]=0;
                if(!strcmp(line,"HELLO"))send("HELLO YS_F4Pro_LED PROTO=1\r\n");
                else if(!strcmp(line,"STATUS"))status();
                else if(LED_App_Command(line)){send("OK\r\n");status();}
                else send("ERR COMMAND\r\n");
            }
            len=0;discard=0;
        }else if(!discard){if(c<32||c>126||len>=sizeof(line)-1){discard=1;len=0;}else line[len++]=c;}
    }
}
