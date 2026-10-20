"""
Flight Ticket Purchasing System - PNR (Passenger Name Record) Generator
IATA standartlarına uygun, okunabilir ve güvenilir PNR kodları üretir ve doğrular.
"""

import hashlib
import re
import secrets
import string
from typing import Optional, Set

# İnsan gözüyle karıştırılması muhtemel karakterler elenmiş alfabetik-sayısal karakter kümesi:
# 0 (sıfır) ve O harfi, 1 (bir) ve I harfi karıştırılabildiği için çıkarılmıştır.
SAFE_PNR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
STANDARD_PNR_ALPHABET = string.ascii_uppercase + string.digits


def generate_pnr(
    length: int = 6,
    prefix: Optional[str] = None,
    safe_chars: bool = True
) -> str:
    """
    Kriptografik olarak güvenli rastgele bir PNR kodu üretir.

    Args:
        length (int): Toplam PNR kodu uzunluğu (Varsayılan: 6).
        prefix (str, optional): PNR başına eklenecek opsiyonel önek (Örn: 'TK').
        safe_chars (bool): Karışabilecek karakterleri (0, O, 1, I) hariç tutar.

    Returns:
        str: Büyük harfli PNR kodu (Örn: 'K7H9P2' veya 'TK82NM')
    """
    alphabet = SAFE_PNR_ALPHABET if safe_chars else STANDARD_PNR_ALPHABET

    if prefix:
        clean_prefix = re.sub(r"[^A-Z0-9]", "", prefix.upper())
        remaining_len = length - len(clean_prefix)
        if remaining_len <= 0:
            raise ValueError(f"Önek uzunluğu ({len(clean_prefix)}) istenen toplam uzunluktan ({length}) küçük olmalıdır.")
        random_part = "".join(secrets.choice(alphabet) for _ in range(remaining_len))
        return f"{clean_prefix}{random_part}"

    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_deterministic_pnr(
    flight_number: str,
    seat_number: str,
    passenger_name: str,
    salt: str = "AERO_FLIGHT_SALT",
    length: int = 6
) -> str:
    """
    Uçuş, koltuk ve yolcu bilgilerinden deterministik (tekrarlanabilir ve öngörülebilir)
    bir PNR kodu türetir. Testler ve eşzamanlılık doğrulamaları için uygundur.
    """
    raw_payload = f"{flight_number}:{seat_number}:{passenger_name}:{salt}".upper()
    hasher = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
    
    # Hash çıktısını güvenli alfabeye eşleme
    alphabet = SAFE_PNR_ALPHABET
    result = []
    # 2 karakterlik hex parçalarını alıp mod uygula
    for i in range(0, length * 2, 2):
        chunk = int(hasher[i:i+2], 16)
        result.append(alphabet[chunk % len(alphabet)])

    return "".join(result)


def validate_pnr(
    pnr: str,
    min_length: int = 5,
    max_length: int = 8,
    strict_safe_chars: bool = False
) -> bool:
    """
    Verilen bir PNR kodunun format kurallarına uygunluğunu denetler.

    Args:
        pnr (str): Denetlenecek PNR kodu.
        min_length (int): Minimum karakter sayısı.
        max_length (int): Maksimum karakter sayısı.
        strict_safe_chars (bool): True ise 0, O, 1, I gibi karakterlerin bulunmadığını da teyit eder.

    Returns:
        bool: PNR geçerli ise True, aksi halde False.
    """
    if not pnr or not isinstance(pnr, str):
        return False

    cleaned = pnr.strip().upper()

    if len(cleaned) < min_length or len(cleaned) > max_length:
        return False

    if strict_safe_chars:
        # Yalnızca güvenli alfabe karakterleri
        pattern = f"^[{SAFE_PNR_ALPHABET}]+$"
    else:
        # Standart büyük harf ve rakamlar
        pattern = r"^[A-Z0-9]+$"

    return bool(re.match(pattern, cleaned))


def generate_unique_pnrs(count: int, length: int = 6, prefix: Optional[str] = None) -> Set[str]:
    """
    Belirtilen adette benzersiz (çakışmasız) PNR kümesi üretir.
    Toplu rezervasyon veya eşzamanlılık yük testlerinde kullanılır.
    """
    pnrs: Set[str] = set()
    max_attempts = count * 10
    attempts = 0

    while len(pnrs) < count and attempts < max_attempts:
        pnrs.add(generate_pnr(length=length, prefix=prefix))
        attempts += 1

    if len(pnrs) < count:
        raise RuntimeError(f"{count} adet benzersiz PNR üretilemedi. Olası kombinasyon sınırı aşıldı.")

    return pnrs
