/* Host-side test: cc -std=c99 -Wall -Wextra -Werror -I.. test/test_ock_frame.c && ./a.out */
#include "ock_frame.h"

#include <stdio.h>
#include <string.h>

static int failures;
#define CHECK(cond) do { if (!(cond)) { printf("FAIL line %d: %s\n", __LINE__, #cond); failures++; } } while (0)

static void hex(const uint8_t *p, char *out) {
  for (size_t i = 0; i < OCK_FRAME_LEN; i++) sprintf(out + 2 * i, "%02x", p[i]);
}

int main(void) {
  CHECK(ock_crc16((const uint8_t *)"123456789", 9) == 0x29B1u);

  /* Golden vectors shared with software/bridge/test_ock_protocol.py. */
  ock_sample_t s = {0x40u | OCK_ST_TEMP_DIE, 513u, 123456u, -1234567, 3712};
  uint8_t f[OCK_FRAME_LEN];
  char text[2 * OCK_FRAME_LEN + 1];
  ock_encode_sample(f, &s);
  hex(f, text);
  CHECK(strcmp(text, "a50114014400010240e201007929edff800e31ae") == 0);

  ock_ident_t id = {0x40u, 1u, 51200u, 550, 1000u, 0x00ABCDEFu, 7u};
  ock_encode_ident(f, &id);
  hex(f, text);
  CHECK(strcmp(text, "a5011402400100c82602e803efcdab00070080a3") == 0);

  printf(failures ? "FAILED\n" : "ock_frame: ok\n");
  return failures != 0;
}
