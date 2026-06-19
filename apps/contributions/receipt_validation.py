import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.utils import timezone


SUCCESS_WORDS = ('muvaffaqiyatli', 'успешно', 'success', 'paid', 'оплачено')
PAYMENT_WORDS = (
    "to'lov",
    "to‘lov",
    "o'tkazma",
    "o‘tkazma",
    'otkazma',
    'tranzaksiya',
    'transfer',
    'payment',
    'перевод',
    'оплата',
    'чек',
)


@dataclass(frozen=True)
class ReceiptValidationResult:
    is_valid: bool
    reason: str
    ocr_text: str
    extracted_amount: Decimal | None = None
    extracted_date: object | None = None
    extracted_card_last4: str = ''
    transaction_id: str = ''


def only_digits(value):
    return ''.join(char for char in str(value or '') if char.isdigit())


def amount_matches(ocr_text, expected_amount):
    expected = only_digits(int(expected_amount))
    return expected in only_digits(ocr_text)


def card_matches(ocr_text, expected_card_last4):
    if not expected_card_last4:
        return True
    return expected_card_last4 in only_digits(ocr_text)


def date_matches(ocr_text, allowed_days=None):
    today = timezone.localdate()
    allowed_days = settings.RECEIPT_ALLOWED_DAYS if allowed_days is None else allowed_days
    allowed_dates = {
        today - timedelta(days=offset)
        for offset in range(allowed_days + 1)
    }
    date_patterns = set()
    for item in allowed_dates:
        date_patterns.update({
            item.strftime('%d.%m.%Y'),
            item.strftime('%d/%m/%Y'),
            item.strftime('%Y-%m-%d'),
            item.strftime('%d.%m.%y'),
            item.strftime('%d/%m/%y'),
        })

    normalized = ocr_text.replace(' ', '')
    return any(pattern in normalized for pattern in date_patterns)


def extract_amount(ocr_text, expected_amount):
    digits = only_digits(int(expected_amount))
    return Decimal(digits) if digits and digits in only_digits(ocr_text) else None


def extract_date(ocr_text):
    patterns = (
        ('%d.%m.%Y', r'\b\d{2}\.\d{2}\.\d{4}\b'),
        ('%d/%m/%Y', r'\b\d{2}/\d{2}/\d{4}\b'),
        ('%Y-%m-%d', r'\b\d{4}-\d{2}-\d{2}\b'),
        ('%d.%m.%y', r'\b\d{2}\.\d{2}\.\d{2}\b'),
        ('%d/%m/%y', r'\b\d{2}/\d{2}/\d{2}\b'),
    )
    for fmt, pattern in patterns:
        match = re.search(pattern, ocr_text)
        if match:
            return datetime.strptime(match.group(), fmt).date()
    return None


def extract_transaction_id(ocr_text):
    match = re.search(r'(?i)(id|transaction|tranzaksiya)[^\w]{0,10}([a-z0-9-]{8,})', ocr_text)
    return match.group(2)[:120] if match else ''


def has_any_word(ocr_text, words):
    lower_text = ocr_text.lower()
    return any(word in lower_text for word in words)


def validate_ocr_text(ocr_text, expected_amount, expected_card_last4):
    if not ocr_text.strip():
        return ReceiptValidationResult(False, 'OCR matn topilmadi.', ocr_text)

    if not has_any_word(ocr_text, SUCCESS_WORDS):
        return ReceiptValidationResult(False, "Muvaffaqiyatli to'lov belgisi topilmadi.", ocr_text)

    if not has_any_word(ocr_text, PAYMENT_WORDS):
        return ReceiptValidationResult(False, "To'lov/transfer belgisi topilmadi.", ocr_text)

    if not amount_matches(ocr_text, expected_amount):
        return ReceiptValidationResult(False, "To'lov summasi mos kelmadi.", ocr_text)

    if not card_matches(ocr_text, expected_card_last4):
        return ReceiptValidationResult(False, 'Karta oxirgi raqamlari mos kelmadi.', ocr_text)

    if not date_matches(ocr_text):
        return ReceiptValidationResult(False, 'Chek sanasi bugungi kunga mos emas.', ocr_text)

    return ReceiptValidationResult(
        True,
        "Chek ma'lumotlari mos.",
        ocr_text,
        extracted_amount=extract_amount(ocr_text, expected_amount),
        extracted_date=extract_date(ocr_text),
        extracted_card_last4=expected_card_last4,
        transaction_id=extract_transaction_id(ocr_text),
    )


def extract_receipt_text_with_ai(image_path, expected_amount, expected_card_last4):
    if not settings.OPENAI_RECEIPT_CHECK_ENABLED or not settings.OPENAI_API_KEY:
        return ReceiptValidationResult(
            False,
            'AI/OCR tekshiruv sozlanmagan.',
            '',
        )

    try:
        from openai import OpenAI

        image_bytes = Path(image_path).read_bytes()
        image_base64 = base64.b64encode(image_bytes).decode('ascii')
        today = timezone.localdate()
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.responses.create(
            model=settings.OPENAI_RECEIPT_MODEL,
            input=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'input_text',
                            'text': (
                                'Extract text from this payment receipt image and validate it. '
                                'It must be a successful bank/payment app transfer receipt, not a random image. '
                                f'Expected amount: {int(expected_amount)} UZS. '
                                f'Expected receiver card last 4 digits: {expected_card_last4 or "unknown"}. '
                                f'Expected date: {today:%Y-%m-%d} or local format {today:%d.%m.%Y}. '
                                'Return only JSON: '
                                '{"ocr_text": "all visible receipt text", "is_receipt": true/false, '
                                '"is_successful_payment": true/false, "reason": "short reason"}'
                            ),
                        },
                        {
                            'type': 'input_image',
                            'image_url': f'data:image/jpeg;base64,{image_base64}',
                        },
                    ],
                }
            ],
        )
        data = json.loads(response.output_text)
    except Exception as exc:
        return ReceiptValidationResult(False, f'AI/OCR xatoligi: {exc}', '')

    ocr_text = str(data.get('ocr_text') or '')
    if not data.get('is_receipt') or not data.get('is_successful_payment'):
        return ReceiptValidationResult(
            False,
            str(data.get('reason') or "Rasm to'lov cheki emas."),
            ocr_text,
        )

    return validate_ocr_text(ocr_text, expected_amount, expected_card_last4)


def validate_payment_receipt(image_path, expected_amount, expected_card_last4):
    return extract_receipt_text_with_ai(
        image_path=image_path,
        expected_amount=expected_amount,
        expected_card_last4=expected_card_last4,
    )
