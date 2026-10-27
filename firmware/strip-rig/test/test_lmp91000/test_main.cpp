#include <unity.h>

#include "lmp91000.h"

void setUp() {}
void tearDown() {}

void test_gain_codes_match_datasheet() {
  uint32_t ohms = 0;
  TEST_ASSERT_TRUE(lmp91000::gainOhms(1, &ohms));
  TEST_ASSERT_EQUAL_UINT32(2750, ohms);
  TEST_ASSERT_TRUE(lmp91000::gainOhms(7, &ohms));
  TEST_ASSERT_EQUAL_UINT32(350000, ohms);
  TEST_ASSERT_FALSE(lmp91000::gainOhms(0, &ohms));
  TEST_ASSERT_FALSE(lmp91000::gainOhms(8, &ohms));
  TEST_ASSERT_EQUAL_HEX8(0x1F, lmp91000::tiacn(7)); /* 350k, 100 ohm load */
  TEST_ASSERT_EQUAL_HEX8(0x07, lmp91000::tiacn(1)); /* power-on default 0x03 has external gain */
}

void test_positive_bias() {
  lmp91000::Reference ref;
  TEST_ASSERT_TRUE(lmp91000::reference(594, 3300, &ref)); /* 18 % of 3.3 V */
  TEST_ASSERT_EQUAL_HEX8(0x3A, ref.refcn);                /* int zero 50 %, positive, BIAS=1010 */
  TEST_ASSERT_EQUAL_INT16(594, ref.biasMv);
  TEST_ASSERT_EQUAL_UINT16(1650, ref.zeroMv);
}

void test_negative_bias_uses_67_percent_zero() {
  lmp91000::Reference ref;
  TEST_ASSERT_TRUE(lmp91000::reference(-132, 3300, &ref)); /* 4 % */
  TEST_ASSERT_EQUAL_HEX8(0x43, ref.refcn);                 /* int zero 67 %, negative, BIAS=0011 */
  TEST_ASSERT_EQUAL_INT16(-132, ref.biasMv);
  TEST_ASSERT_EQUAL_UINT16(2211, ref.zeroMv);
}

void test_zero_bias_and_limits() {
  lmp91000::Reference ref;
  TEST_ASSERT_TRUE(lmp91000::reference(0, 3300, &ref));
  TEST_ASSERT_EQUAL_HEX8(0x30, ref.refcn);
  TEST_ASSERT_TRUE(lmp91000::reference(792, 3300, &ref));
  TEST_ASSERT_EQUAL_HEX8(0x3D, ref.refcn);
  TEST_ASSERT_FALSE(lmp91000::reference(900, 3300, &ref));
  TEST_ASSERT_FALSE(lmp91000::reference(-900, 3300, &ref));
}

void test_temperature_transfer() {
  int16_t cc = 0;
  TEST_ASSERT_TRUE(lmp91000::tempCentiC(1359, &cc)); /* 25 C in Table 1 */
  TEST_ASSERT_INT16_WITHIN(30, 2500, cc);
  TEST_ASSERT_FALSE(lmp91000::tempCentiC(300, &cc));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_gain_codes_match_datasheet);
  RUN_TEST(test_positive_bias);
  RUN_TEST(test_negative_bias_uses_67_percent_zero);
  RUN_TEST(test_zero_bias_and_limits);
  RUN_TEST(test_temperature_transfer);
  return UNITY_END();
}
