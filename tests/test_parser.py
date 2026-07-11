import unittest

from telegramonline.parser import parse_message, parse_message_group, split_multi_ad_blocks


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

    # ===== تست‌های جدید برای باگ سال میلادی =====

    def test_miladi_year_alone_is_not_price(self) -> None:
        ad = parse_message(
            "m1",
            """
            مزدا ez6 سفید
            ۲۰۲۵
            پلاک مدارک آماده
            09191599213
            """,
        )
        self.assertEqual(ad.vehicle_key, "mazda_ez6")
        self.assertIsNone(ad.price_million)
        self.assertEqual(ad.year, 2025)

    def test_miladi_2026_corolla_not_price(self) -> None:
        ad = parse_message(
            "m2",
            """
            کرولا کراس نیوفیس سفید
            ۲۰۲۶
            با پلاک و مدارک
            قابل تحویل
            خوش قیمت 🔥🔥🔥🔥
            09131631070
            """,
        )
        self.assertIsNone(ad.price_million)
        self.assertEqual(ad.year, 2026)

    def test_shamsi_year_present_2040_still_price(self) -> None:
        # وقتی سال شمسی در پیام هست، عدد 2040 قیمت واقعی است
        ad = parse_message(
            "m3",
            "شاهین دنده ای سفید ۱۴۰۵ برج ۴\n2020\n09122148772",
        )
        self.assertEqual(ad.price_million, 2020)

    def test_single_digit_inside_sentence_is_not_price(self) -> None:
        # «سند آماده ۱ ساعته» نباید ۱۰۰۰ میلیون حساب شود
        ad = parse_message(
            "bug1",
            """
            کوییک gxrl سفید مشکی با رینگ شرکتی
            ۴۰۴/۱۰
            گارانتی فعال
            پلاک گیلان با میخ لاستیک سند آماده ۱ ساعته
            🔥🔥
            موجود نمایشگاه
            09113310946
            """,
        )
        self.assertIsNone(ad.price_million)

    def test_year_month_compact_notation_not_price(self) -> None:
        # «۱۴۰۵،۲» یعنی سال،برج نه قیمت؛ قیمت واقعی خط بعدی (۱۶۹۵) است
        ad = parse_message(
            "bug1b",
            "۲۰۷ تیو۳\n۱۴۰۵،۲\nفردایی با طلایی نقدی\n۱۶۹۵\nحسن پور",
        )
        self.assertEqual(ad.price_million, 1695)

    def test_dedup_key_ignores_spacing_and_case(self) -> None:
        # همان آگهی با فاصله‌گذاری/بزرگی حروف متفاوت باید کلید یکسان بدهد
        ad_a = parse_message("dup_a", "کوییکgxrسفید مدل403کارکرد42هزار 1010\n09195424677")
        ad_b = parse_message("dup_b", "🚘 کوییک GXR سفید مدل ۴۰۳ کارکرد ۴۲ هزار\n۱۰۱۰ 📞 09195424677")
        self.assertEqual(ad_a.dedup_key, ad_b.dedup_key)

    def test_multi_ad_message_splits_into_separate_ads(self) -> None:
        # یک پیام تلگرام با چند آگهی جداشده با خط ______ نباید یکی حساب شود
        text = (
            "چانگان cs55 خاکستری۲۰۲۴ گارانتی غیرفعال✅\n🔥🔥🔥خوش قیمت\n📲09113763302\n"
            "______________________________\n"
            "۲۰۷ هیدرولیک سفید۴۰۵ روز داغ✅\n🔥🔥🔥\n📲09113763302\n"
            "______________________________\n"
            "دنا اتومات اپشنال سفید ۴۰۵ روز ✅\n🔥🔥🔥\n📲09113763302"
        )
        ads = parse_message_group("999", text, source="live")
        self.assertEqual(len(ads), 3)
        self.assertEqual(ads[0].vehicle_key, "changan_cs55")
        self.assertEqual(ads[1].vehicle_key, "peugeot_207")
        self.assertEqual(ads[2].vehicle_key, "dena")
        # هر سه باید همان source_message_id واقعی را داشته باشند (یک پیام واحدند)
        self.assertTrue(all(ad.source_message_id == "999" for ad in ads))
        # اما متن‌های خامشان باید متفاوت باشد (برای یکتایی در دیتابیس)
        self.assertEqual(len({ad.raw_text for ad in ads}), 3)

    def test_single_ad_message_not_split(self) -> None:
        # پیام معمولی بدون خط جداکننده باید دست‌نخورده بماند
        text = "پراید صبا سفید مدل 1400\nقیمت 550\n09120000000"
        blocks = split_multi_ad_blocks(text)
        self.assertEqual(blocks, [text])

    def test_short_decorative_line_not_treated_as_separator(self) -> None:
        # خط تزئینی کوتاه (کمتر از ۸ کاراکتر) نباید جداکننده حساب شود
        text = "پراید صفید\n🔥🔥🔥\nقیمت 700\n09120000001"
        blocks = split_multi_ad_blocks(text)
        self.assertEqual(len(blocks), 1)

    def test_multi_ad_without_separator_splits_by_price_lines(self) -> None:
        # پیام چندتایی که به‌جای خط جداکننده، هر آگهی با یک خط قیمتِ رنگی
        # (🔴 عدد) تمام می‌شود؛ نباید قیمت آگهی اول به بقیه بچسبد
        text = (
            "تانک ۳۰۰ مشکی ۴۰۴ برج۱۱ کارکرد ۵/۰۰۰ با لوازم\n\n🔴۱۰.۲۰۰.۰۰۰\n\n"
            "چانگان cs55 وارداتی مشکی ۲۰۲۵ روز\nبا کارشناسی سند اماده\n🔴۵.۸۰۰.۰۰۰"
        )
        ads = parse_message_group("m", text, source="live")
        self.assertEqual(len(ads), 2)
        changan = next(ad for ad in ads if ad.vehicle_key == "changan_cs55")
        self.assertEqual(changan.price_million, 5800)

    def test_full_date_not_treated_as_price(self) -> None:
        # «۱۴۰۵/۰۴/۱۷» یک تاریخ کامل است؛ تکه‌ی «۰۴/۱۷» نباید قیمت ۴۰۱۷ شود
        ad = parse_message(
            "date_bug",
            "با آرزوی سلامتی\n1405/04/17\nلاماری هیبرید مشکی پلاک تهران. 2025\n09124992470",
        )
        self.assertIsNone(ad.price_million)

    def test_bare_phone_line_does_not_split_single_ad(self) -> None:
        # شماره تلفن به‌تنهایی روی یک خط، نباید مرز آگهی حساب شود
        text = "پراید سفید مدل 1400\n700\n09120000000"
        blocks = split_multi_ad_blocks(text)
        self.assertEqual(blocks, [text])

    def test_date_line_is_not_ad_boundary_or_price(self) -> None:
        # خط تاریخ تنها (۱۴۰۵/۰۴/۱۸) نه مرز آگهی است نه قیمت
        text = (
            "با آرزوی سلامتی\n\n1405/04/18\n\n"
            "لاماری هیبرید مشکی پلاک تهران. 2025\n\n"
            "چانگان Uni T سفید و مشکی روز. 2026\n\n09124992470"
        )
        blocks = split_multi_ad_blocks(text)
        self.assertEqual(len(blocks), 1)
        ad = parse_message("d1", text)
        self.assertIsNone(ad.price_million)

    def test_installment_cheque_dates_not_price(self) -> None:
        # پیام حواله اقساطی: چک‌های مورخ ۱۴۰۵/۰۵/۱۶ نباید قیمت بسازند
        ad = parse_message(
            "d2",
            "موجودی حواله مورخ\n۱۴۰۵/۰۴/۱۷\n🛑ایگل کاردکس\nپیش پرداخت ۱/۵۰۰\n"
            "چک ۴۰۰مورخ۱۴۰۵/۰۵/۱۶\nچک ۴۰۰مورخ ۱۴۰۵/۰۶/۱۶\n📲09120816670",
        )
        self.assertIsNone(ad.price_million)

    def test_money_bag_marker_line_is_ad_boundary(self) -> None:
        # خط «💰950» (بدون جداکننده هزارگان) هم باید مرز آگهی حساب شود
        text = (
            "کوییک s سفید ۴۰۲ کارکرد ۶۵/۰۰۰ بدون رنگ\n💰950\n\n"
            "ساینا ۹۹ سفید کارکرد ۱۳۵/۰۰۰\n💰780\n\n"
            "چانگان ۹۶ سه چهار لکه رنگ کارکرد ۱۹۰/۰۰۰\n💰1/840"
        )
        ads = parse_message_group("m", text)
        self.assertEqual(len(ads), 3)
        changan = next(ad for ad in ads if "چانگان" in ad.raw_text)
        self.assertEqual(changan.price_million, 1840)
        self.assertIsNone(changan.year)
        self.assertIsNone(changan.color)

    def test_compact_year_month_slash_not_price(self) -> None:
        # «۴۰۵/۲» یعنی سال ۱۴۰۵ برج ۲ — نباید قیمت ۴۰۵۲ شود
        ad = parse_message(
            "ym",
            "چانگان CS55 سفید ۴۰۵/۲ قابل تحویل\n\n🔥(مونتاژ)\n\n09352345756",
        )
        self.assertIsNone(ad.price_million)
        self.assertEqual(ad.year, 1405)


if __name__ == "__main__":
    unittest.main()