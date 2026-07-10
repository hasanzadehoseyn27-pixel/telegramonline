import unittest

from telegramonline.parser import parse_message


class ParserTests(unittest.TestCase):
    def test_soren_slash_price(self) -> None:
        ad = parse_message(
            "1",
            """
            سورن موتور پارس برقی ۴۰۵ برج ۴
            قابل تحویل
            کفی
            1/643/000
            09103351045
            """,
        )
        self.assertEqual(ad.vehicle_key, "soren")
        self.assertEqual(ad.year, 1405)
        self.assertEqual(ad.month, 4)
        self.assertEqual(ad.price_million, 1643)
        self.assertEqual(ad.phone, "09103351045")
        self.assertEqual(ad.status, "sale")

    def test_price_line_plain_number(self) -> None:
        ad = parse_message(
            "4",
            """
            شاهین دنده ای با سانروف سفید ۱۴۰۵ برج ۴
            2040
            09122148772
            """,
        )
        self.assertEqual(ad.vehicle_key, "shahin")
        self.assertEqual(ad.price_million, 2040)
        self.assertEqual(ad.color, "سفید")

    def test_skip_buyer_message(self) -> None:
        ad = parse_message("35", "خریدار فوری پراید وانت gx پاششی ۴۰۵ خوش قیمت\n09168190900")
        self.assertEqual(ad.vehicle_key, "pride_van")
        self.assertEqual(ad.status, "buyer")
        self.assertLess(ad.confidence, 0.55)

    def test_skip_mileage_as_price(self) -> None:
        ad = parse_message(
            "30",
            """
            دنا اتومات فول مشکی
            مدل  1400
            37.000 واقعی به شرط
            بدون نقطه
            09181664320
            """,
        )
        self.assertEqual(ad.vehicle_key, "dena")
        self.assertEqual(ad.year, 1400)
        self.assertIsNone(ad.price_million)

    def test_one_digit_price_line(self) -> None:
        ad = parse_message(
            "5",
            """
            سورن دوگانه مخزن بزرگ
            سیمی 1405/3
            فردایی
            2
            09188570500
            """,
        )
        self.assertEqual(ad.vehicle_key, "soren")
        self.assertEqual(ad.price_million, 2000)

    def test_spaced_billion_price(self) -> None:
        ad = parse_message(
            "x",
            """
            دنا اتومات اپشنال سفید
            2 545 000 000🔥🔥🔥
            0912 406 9005
            """,
        )
        self.assertEqual(ad.price_million, 2545)
        self.assertEqual(ad.phone, "09124069005")

    def test_spaced_phone_is_not_price(self) -> None:
        ad = parse_message(
            "y",
            """
            چانگان مشکی cs55 مونتاژ ۱۴۰۴
            کارکرد ۲ هزار مشابه صفر
            0912 18 18 428
            """,
        )
        self.assertIsNone(ad.price_million)
        self.assertEqual(ad.phone, "09121818428")

    def test_km_is_not_price(self) -> None:
        ad = parse_message("km", "تارا v4 مشکی ۴۰۴ برج ۱۱\n۴۱۰ km\n09120285488")
        self.assertIsNone(ad.price_million)

    def test_degree_one_is_not_price(self) -> None:
        ad = parse_message("degree", "دنا اتومات فول مشکی\nمدل ۱۴۰۰\nدرجه ۱\n09181664320")
        self.assertIsNone(ad.price_million)

    def test_market_report_is_spam(self) -> None:
        ad = parse_message(
            "market",
            "آخرین بروزرسانی قیمت خودروهای پرفروش\nقیمت دلار: 175.000\nسورن(XU7P) برق:1.640",
        )
        self.assertEqual(ad.status, "spam")

    def test_trim_number_is_not_price(self) -> None:
        ad = parse_message("trim", "تارا v1 سفید\n۱۴۰۵ برج روز فردا کفی\n09116004863")
        self.assertIsNone(ad.price_million)
        self.assertEqual(ad.trim, "v1")


if __name__ == "__main__":
    unittest.main()
