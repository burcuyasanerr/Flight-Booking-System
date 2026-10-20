"""
Flight Ticket Purchasing System - PDF Generator
ReportLab kullanarak profesyonel, modern ve IATA uyumlu Elektronik Uçuş Bileti / Biniş Kartı üretir.
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional, Union

import qrcode
from PIL import Image
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    from .models import FlightTicket
except ImportError:
    from models import FlightTicket


# --- FONT YAPILANDIRMASI (TÜRKÇE KARAKTER DESTEĞİ) ---
def _setup_fonts() -> tuple[str, str]:
    """
    Sistemdeki TrueType fontları (Arial vb.) arayarak Türkçe karakterleri
    kusursuz görüntüleyecek fontları ReportLab sistemine kaydeder.
    """
    regular_font = "Helvetica"
    bold_font = "Helvetica-Bold"

    font_candidates = [
        # Windows
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        # Linux
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]

    for reg_path, bld_path in font_candidates:
        if os.path.exists(reg_path) and os.path.exists(bld_path):
            try:
                pdfmetrics.registerFont(TTFont("FlightCustomRegular", reg_path))
                pdfmetrics.registerFont(TTFont("FlightCustomBold", bld_path))
                regular_font = "FlightCustomRegular"
                bold_font = "FlightCustomBold"
                break
            except Exception:
                continue

    return regular_font, bold_font


FONT_REGULAR, FONT_BOLD = _setup_fonts()

# --- RENK PALETİ ---
PRIMARY_NAVY = colors.HexColor("#0B192C")      # Kurumsal Koyu Lacivert
SECONDARY_BLUE = colors.HexColor("#1E3E62")    # Vurgu Mavisi
ACCENT_ORANGE = colors.HexColor("#FF6500")     # Havacılık Turuncusu
LIGHT_BG = colors.HexColor("#F8F9FA")          # Açık Gri Kart Arka Planı
BORDER_GRAY = colors.HexColor("#E2E8F0")       # İnce Kenarlık Grisi
TEXT_DARK = colors.HexColor("#1E293B")         # Ana Metin Rengi
TEXT_MUTED = colors.HexColor("#64748B")        # İkincil / Açıklama Grisi
SUCCESS_GREEN = colors.HexColor("#059669")     # Onay Yeşili


def _create_route_vector(width: float = 120, height: float = 20) -> Drawing:
    """
    Kalkış ve varış noktaları arasında şık bir vektörel uçuş rotası çizgisi çizer.
    """
    d = Drawing(width, height)
    mid_y = height / 2.0
    # Kalkış noktası dairesi
    d.add(Circle(8, mid_y, 3, fillColor=ACCENT_ORANGE, strokeColor=None))
    # Kesikli rota çizgisi
    line = Line(14, mid_y, width - 14, mid_y, strokeColor=colors.HexColor("#94A3B8"), strokeWidth=1.5, strokeDashArray=[4, 3])
    d.add(line)
    # Varış ok başı
    poly = Polygon(
        [width - 14, mid_y - 4, width - 4, mid_y, width - 14, mid_y + 4],
        fillColor=ACCENT_ORANGE,
        strokeColor=None,
    )
    d.add(poly)
    return d


def _create_qr_image(ticket: FlightTicket, size: int = 140) -> RLImage:
    """
    PNR ve bilet doğrulama verilerini içeren yüksek çözünürlüklü QR kod üretir.
    """
    qr_payload = (
        f"FLIGHT-TICKET|PNR:{ticket.ticket.pnr_code}|"
        f"FLIGHT:{ticket.flight.flight_number}|"
        f"PASSENGER:{ticket.passenger.full_name}|"
        f"SEAT:{ticket.ticket.seat_number}|"
        f"DATE:{ticket.flight.departure_datetime.strftime('%Y-%m-%d')}|"
        f"STATUS:{ticket.ticket.ticket_status.value}"
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=1,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)

    pil_img = qr.make_image(fill_color="#0B192C", back_color="white")
    img_buffer = io.BytesIO()
    pil_img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    # ReportLab Image flowable nesnesi
    return RLImage(img_buffer, width=3.0 * cm, height=3.0 * cm)


def _create_barcode(ticket: FlightTicket) -> Table:
    """
    Biniş kapısı tarayıcıları için Code128 barkod akışı üretir.
    """
    barcode_val = f"{ticket.ticket.pnr_code}{ticket.ticket.seat_number}".replace(" ", "")
    barcode_drawing = createBarcodeDrawing(
        "Code128",
        value=barcode_val,
        width=180,
        height=32,
        humanReadable=False,
        barFillColor=PRIMARY_NAVY,
    )
    return barcode_drawing


class TicketPDFBuilder:
    """
    Uçuş bileti PDF dokümanını parçalar halinde inşa eden yapılandırıcı sınıf.
    """

    def __init__(self, ticket: FlightTicket):
        self.ticket = ticket
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        """Metin stillerini tanımlar."""
        self.style_header_title = ParagraphStyle(
            "HeaderTitle",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=15,
            leading=18,
            textColor=colors.white,
        )
        self.style_header_sub = ParagraphStyle(
            "HeaderSub",
            parent=self.styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#CBD5E1"),
        )
        self.style_pnr_box = ParagraphStyle(
            "PNRBox",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=16,
            leading=20,
            alignment=2,  # Sağ
            textColor=ACCENT_ORANGE,
        )
        self.style_label = ParagraphStyle(
            "CardLabel",
            parent=self.styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=9.5,
            textColor=TEXT_MUTED,
        )
        self.style_val_bold = ParagraphStyle(
            "CardValueBold",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=11,
            leading=13,
            textColor=TEXT_DARK,
        )
        self.style_val_large = ParagraphStyle(
            "CardValueLarge",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=18,
            leading=20,
            textColor=PRIMARY_NAVY,
        )
        self.style_val_huge = ParagraphStyle(
            "CardValueHuge",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=24,
            textColor=PRIMARY_NAVY,
        )
        self.style_route_arrow = ParagraphStyle(
            "RouteArrow",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=12,
            leading=14,
            alignment=1,  # Orta
            textColor=ACCENT_ORANGE,
        )
        self.style_section_title = ParagraphStyle(
            "SectionTitle",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            leading=13,
            textColor=PRIMARY_NAVY,
        )
        self.style_info_text = ParagraphStyle(
            "InfoText",
            parent=self.styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=10.5,
            textColor=TEXT_DARK,
        )
        self.style_info_text_right = ParagraphStyle(
            "InfoTextRight",
            parent=self.styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=6.5,
            leading=9.5,
            alignment=2,  # Sağ
            textColor=TEXT_MUTED,
        )

    def build_header(self) -> Table:
        """Üst başlık ve PNR rozeti bloğu"""
        airline = self.ticket.flight.airline_name.upper()
        pnr = self.ticket.ticket.pnr_code
        status_text = self.ticket.ticket.ticket_status.value

        col1 = Paragraph(
            f"<b>{airline}</b><br/>"
            f"<font size=8 color='#E2E8F0'>ELEKTRONİK UÇUŞ BİLETİ & BİNİŞ KARTI / E-TICKET & BOARDING PASS</font>",
            self.style_header_title,
        )
        col2 = Paragraph(
            f"<font size=8 color='#94A3B8'>REZERVASYON (PNR)</font><br/>"
            f"<b>{pnr}</b><br/>"
            f"<font size=7 color='#4ADE80'>DURUM: {status_text}</font>",
            self.style_pnr_box,
        )

        header_table = Table([[col1, col2]], colWidths=[11.5 * cm, 6.5 * cm])
        header_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_NAVY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ])
        )
        return header_table

    def build_boarding_pass_card(self) -> Table:
        """
        Ana Biniş Kartı (Boarding Pass) görsel kartı.
        Sol tarafta detaylı rota ve biniş bilgileri, sağ tarafta koparılabilir kupon (stub) yer alır.
        """
        f = self.ticket.flight
        p = self.ticket.passenger
        t = self.ticket.ticket

        # --- SOL TARAF: GÜZERGAH VE UÇUŞ DETAYI ---
        dep_time_str = f.departure_datetime.strftime("%H:%M")
        dep_date_str = f.departure_datetime.strftime("%d.%m.%Y")
        arr_time_str = f.arrival_datetime.strftime("%H:%M")
        arr_date_str = f.arrival_datetime.strftime("%d.%m.%Y")
        boarding_time_str = f.boarding_time.strftime("%H:%M") if f.boarding_time else "--:--"

        route_vector = _create_route_vector(width=115, height=18)
        mid_column = [
            Paragraph(f"<font size=7.5 color='#64748B'>UÇUŞ / FLIGHT:</font> <b>{f.flight_number}</b>", self.style_route_arrow),
            Spacer(1, 1 * mm),
            route_vector,
            Spacer(1, 1 * mm),
            Paragraph(f"<font size=7 color='#0B192C'>Süre: <b>{f.duration_formatted}</b></font>", self.style_route_arrow),
        ]

        route_table_data = [
            [
                Paragraph(f"<font size=7 color='#64748B'>KALKIŞ / ORIGIN</font><br/>"
                          f"<b>{f.origin_code}</b><br/>"
                          f"<font size=8><b>{dep_time_str}</b></font><br/>"
                          f"<font size=7 color='#64748B'>{dep_date_str}</font><br/>"
                          f"<font size=6.5 color='#475569'>{f.origin_name[:24]}</font>", self.style_val_huge),
                mid_column,
                Paragraph(f"<font size=7 color='#64748B'>VARIŞ / DESTINATION</font><br/>"
                          f"<b>{f.destination_code}</b><br/>"
                          f"<font size=8><b>{arr_time_str}</b></font><br/>"
                          f"<font size=7 color='#64748B'>{arr_date_str}</font><br/>"
                          f"<font size=6.5 color='#475569'>{f.destination_name[:24]}</font>", self.style_val_huge),
            ]
        ]
        route_table = Table(route_table_data, colWidths=[3.7 * cm, 4.4 * cm, 3.7 * cm])
        route_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )

        # Yolcu & Koltuk & Kapı 1. Tablo (Üst Satır)
        row1_data = [
            [
                Paragraph("YOLCU ADI SOYADI / PASSENGER", self.style_label),
                Paragraph("KOLTUK / SEAT", self.style_label),
                Paragraph("KAPI / GATE", self.style_label),
                Paragraph("BİNİŞ SAATİ / BOARDING", self.style_label),
            ],
            [
                Paragraph(f"<b>{p.full_name}</b>", self.style_val_bold),
                Paragraph(f"<font color='#0B192C'><b>{t.seat_number}</b></font>", self.style_val_large),
                Paragraph(f"<font color='#FF6500'><b>{f.gate or '--'}</b></font>", self.style_val_large),
                Paragraph(f"<b>{boarding_time_str}</b>", self.style_val_bold),
            ],
        ]
        row1_table = Table(row1_data, colWidths=[4.7 * cm, 2.2 * cm, 2.4 * cm, 2.5 * cm])
        row1_table.setStyle(
            TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ])
        )

        # 2. Tablo (Alt Satır: Kabin, Bagaj, Terminal, Model)
        row2_data = [
            [
                Paragraph("KABİN SINIFI / CLASS", self.style_label),
                Paragraph("BAGAJ HAKKI / BAGGAGE", self.style_label),
                Paragraph("TERMINAL", self.style_label),
                Paragraph("UÇAK MODELİ / AIRCRAFT", self.style_label),
            ],
            [
                Paragraph(f"<b>{t.cabin_class.value}</b>", self.style_val_bold),
                Paragraph(f"<b>{t.baggage_allowance}</b>", self.style_val_bold),
                Paragraph(f"<b>{f.terminal or 'T1'}</b>", self.style_val_bold),
                Paragraph(f"<b>{f.aircraft_type or 'Standart'}</b>", self.style_val_bold),
            ],
        ]
        row2_table = Table(row2_data, colWidths=[2.8 * cm, 4.3 * cm, 2.0 * cm, 2.7 * cm])
        row2_table.setStyle(
            TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ])
        )

        left_content = [
            route_table,
            Spacer(1, 3 * mm),
            HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY, spaceBefore=2, spaceAfter=4),
            row1_table,
            Spacer(1, 2 * mm),
            row2_table,
        ]

        # --- SAĞ TARAF: BİNİŞ KARTI KUPONU (STUB) & QR KOD & BARKOD ---
        qr_flowable = _create_qr_image(self.ticket)
        barcode_flowable = _create_barcode(self.ticket)

        stub_data = [
            [Paragraph("<font size=7 color='#64748B'>KUPON / PASSENGER STUB</font>", self.style_label)],
            [Paragraph(f"<b>{p.last_name.upper()} / {p.first_name.upper()}</b>", self.style_val_bold)],
            [Paragraph(f"<font size=7 color='#64748B'>UÇUŞ:</font> <b>{f.flight_number}</b> &nbsp;&nbsp; "
                       f"<font size=7 color='#64748B'>PNR:</font> <font color='#FF6500'><b>{t.pnr_code}</b></font>", self.style_info_text)],
            [Paragraph(f"<b>{f.origin_code} &gt; {f.destination_code}</b>", self.style_val_bold)],
            [Paragraph(f"<font size=7 color='#64748B'>KOLTUK:</font> <b>{t.seat_number}</b> &nbsp;|&nbsp; "
                       f"<font size=7 color='#64748B'>KAPI:</font> <b>{f.gate or '--'}</b>", self.style_info_text)],
            [qr_flowable],
            [barcode_flowable],
        ]
        stub_table = Table(stub_data, colWidths=[5.4 * cm])
        stub_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ])
        )

        # Ana Kart Birleşimi (Sol + Ayraç Çizgisi + Sağ Stub)
        main_card_table = Table(
            [[left_content, stub_table]],
            colWidths=[12.2 * cm, 5.8 * cm],
        )
        main_card_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_GRAY),
                ("LINEBEFORE", (1, 0), (1, -1), 1, colors.HexColor("#CBD5E1"), 0, (2, 2)),  # Kesik çizgi efekti
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        return main_card_table

    def build_financial_table(self) -> Table:
        """Ücret, vergi ve ödeme dökümü tablosu"""
        t = self.ticket.ticket
        currency = t.currency

        data = [
            [
                Paragraph("<b>ÜCRET KALEMİ / FARE BREAKDOWN</b>", self.style_section_title),
                Paragraph("<b>TUTAR / AMOUNT</b>", self.style_section_title),
                Paragraph("<b>ÖDEME BİLGİSİ / PAYMENT DETAILS</b>", self.style_section_title),
                Paragraph("<b>AÇIKLAMA / NOTE</b>", self.style_section_title),
            ],
            [
                Paragraph("Taban Bilet Ücreti", self.style_info_text),
                Paragraph(f"{t.base_price:,.2f} {currency}", self.style_info_text),
                Paragraph(f"Ödeme Yöntemi: <b>{t.payment_method}</b>", self.style_info_text),
                Paragraph("Elektronik Tahsilat", self.style_info_text),
            ],
            [
                Paragraph("Havalimanı & Güvenlik Vergileri", self.style_info_text),
                Paragraph(f"{t.tax_amount:,.2f} {currency}", self.style_info_text),
                Paragraph(f"İşlem Tarihi: <b>{t.booking_date.strftime('%d.%m.%Y %H:%M')}</b>", self.style_info_text),
                Paragraph("KDV / Harçlar Dahil", self.style_info_text),
            ],
            [
                Paragraph("<b>TOPLAM TUTAR (ÖDENDİ)</b>", self.style_val_bold),
                Paragraph(f"<font color='#059669'><b>{t.total_price:,.2f} {currency}</b></font>", self.style_val_bold),
                Paragraph("Fatura Durumu: <b>Düzenlendi</b>", self.style_info_text),
                Paragraph("İade/Değişiklik kurallarına tabidir", self.style_info_text),
            ],
        ]

        fin_table = Table(data, colWidths=[5.5 * cm, 3.5 * cm, 5.0 * cm, 4.0 * cm])
        fin_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                ("LINEBELOW", (0, -1), (-1, -1), 1, PRIMARY_NAVY),
            ])
        )
        return fin_table

    def build_notices_section(self) -> Table:
        """Yolcu için önemli kurallar ve bilgilendirmeler paneli"""
        notices = [
            "• <b>Havalimanı Varış Zamanı:</b> İç hat uçuşlarında kalkıştan en az 2 saat, dış hat uçuşlarında en az 3 saat önce havalimanında bulunmanız önerilir.",
            "• <b>Biniş Kapısı Kapanış Saati:</b> Uçağa biniş kapıları (Gate) uçuş kalkış saatinden <b>20 dakika önce</b> kesin olarak kapatılır.",
            "• <b>Kimlik İbrazı:</b> Uçuşa kabul için fotoğraflı resmi T.C. Kimlik Kartı, Ehliyet veya Pasaport aslı ibraz edilmelidir.",
            "• <b>Bagaj Güvenliği:</b> El bagajınızda 100 ml üzeri sıvı, yanıcı ve kesici alet taşınması uluslararası havacılık kuralları gereğince yasaktır.",
            "• <b>Elektronik Bilet Doğrulama:</b> Bu bilet üzerindeki QR kod ve barkod biniş kapısı optik okuyucularında doğrudan taranabilir.",
        ]

        cell_content = [Paragraph("<font color='#0B192C'><b>ÖNEMLİ YOLCU BİLGİLENDİRMELERİ & KURALLAR</b></font>", self.style_section_title)]
        for item in notices:
            cell_content.append(Spacer(1, 1.2 * mm))
            cell_content.append(Paragraph(item, self.style_info_text))

        table = Table([[cell_content]], colWidths=[18.0 * cm])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),  # Hafif uyarıcı sarımsı arka plan
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        return table

    def build_footer(self) -> Table:
        """Alt bilgi ve güvenlik damgası"""
        issue_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        doc_hash = f"VERIFY-{self.ticket.ticket.pnr_code}-{self.ticket.ticket.seat_number}"

        left_text = Paragraph(
            f"<font size=6.5 color='#64748B'>"
            f"Düzenlenme Zamanı: {issue_time} | Belge No: {doc_hash}<br/>"
            f"Müşteri Hizmetleri Destek: 0850 000 00 00 | Web: www.flightbooker-team19.com"
            f"</font>",
            self.style_info_text,
        )
        right_text = Paragraph(
            "Bu belge IATA standartlarına uygun resmi e-bilet makbuzudur.<br/>Sayfa 1 / 1",
            self.style_info_text_right,
        )

        footer_table = Table([[left_text, right_text]], colWidths=[12.0 * cm, 6.0 * cm])
        footer_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        return footer_table

    def generate(self, target: Union[str, Path, BinaryIO]):
        """PDF belgesini derler ve hedefe yazar."""
        doc = SimpleDocTemplate(
            target,
            pagesize=A4,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm,
        )

        story = [
            self.build_header(),
            Spacer(1, 4 * mm),
            self.build_boarding_pass_card(),
            Spacer(1, 5 * mm),
            Paragraph("<b>ÜCRET VE ÖDEME AYRINTILARI</b>", self.style_section_title),
            Spacer(1, 2 * mm),
            self.build_financial_table(),
            Spacer(1, 5 * mm),
            self.build_notices_section(),
            Spacer(1, 4 * mm),
            HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY, spaceBefore=2, spaceAfter=2),
            self.build_footer(),
        ]

        doc.build(story)


def generate_ticket_pdf(ticket: FlightTicket, output_path: Union[str, Path]) -> str:
    """
    Verilen FlightTicket modeli için PDF dosyası oluşturur ve dosya yolunu döner.

    Args:
        ticket (FlightTicket): Bilet verisi modeli.
        output_path (Union[str, Path]): PDF'in kaydedileceği hedef yol.

    Returns:
        str: Oluşturulan dosyanın mutlak dosya yolu.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    builder = TicketPDFBuilder(ticket)
    builder.generate(str(path))
    return str(path)


def generate_ticket_pdf_bytes(ticket: FlightTicket) -> bytes:
    """
    Verilen FlightTicket modeli için PDF'i bellekte (in-memory) üretip bayt dizisi (bytes) döner.
    Web servisleri ve API yanıtları için uygundur.

    Args:
        ticket (FlightTicket): Bilet verisi modeli.

    Returns:
        bytes: Üretilen PDF dosya içeriği.
    """
    buffer = io.BytesIO()
    builder = TicketPDFBuilder(ticket)
    builder.generate(buffer)
    return buffer.getvalue()
