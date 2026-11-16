import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
from ocr_support import extract_missing_pages, find_tessdata, parse_page_numbers
from pdf_highlights import keyword_rects


class OCRSupportTests(unittest.TestCase):
    def test_selective_pages_and_safe_cancel(self):
        self.assertEqual(parse_page_numbers("2, 5-7, 7",10),[2,5,6,7])
        with self.assertRaises(ValueError): parse_page_numbers("9-4",10)
        with self.assertRaises(ValueError): parse_page_numbers("11",10)
        results,errors=extract_missing_pages([("unused.pdf","hash",[1])],Path("tessdata"),
            should_cancel=lambda:True)
        self.assertEqual((results,errors),([],[]))
    def test_find_tessdata_from_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory,"eng.traineddata").write_bytes(b"test")
            with patch("ocr_support.__file__",str(Path(directory)/"ocr_support.py")), patch.dict("os.environ",{"TESSDATA_PREFIX":directory}):
                self.assertEqual(find_tessdata(),Path(directory))

    def test_extract_uses_ocr_textpage_and_page_number(self):
        page=MagicMock()
        page.get_text.return_value="OCR text from the scanned page"
        pdf=MagicMock(); pdf.__enter__.return_value=pdf; pdf.__getitem__.return_value=page
        with patch("ocr_support.fitz.open",return_value=pdf):
            results,errors=extract_missing_pages([("report.pdf","hash",[3])],Path("tessdata"))
        self.assertEqual(errors,[])
        self.assertEqual(results,[("report.pdf","hash",3,"OCR text from the scanned page")])
        pdf.__getitem__.assert_called_once_with(2)
        page.get_textpage_ocr.assert_called_once_with(language="eng",dpi=200,full=True,tessdata="tessdata")

    def test_real_ocr_reads_image_only_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_path=Path(directory)/"scan.pdf"
            source=fitz.open(); page=source.new_page()
            page.insert_text((72,100),"ENVIRONMENTAL COMPLIANCE RISK",fontsize=22)
            image=page.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes("png")
            scanned=fitz.open(); target=scanned.new_page(width=page.rect.width,height=page.rect.height)
            target.insert_image(target.rect,stream=image)
            scanned.save(pdf_path); scanned.close(); source.close()
            with fitz.open(pdf_path) as opened:
                self.assertEqual(opened[0].get_text("text"),"")
            results,errors=extract_missing_pages([(str(pdf_path),"hash",[1])],find_tessdata())
            self.assertEqual(errors,[])
            self.assertIn("ENVIRONMENTAL COMPLIANCE RISK",results[0][3])
            with fitz.open(pdf_path) as opened:
                rects = keyword_rects(opened[0], ["COMPLIANCE RISK"], ocr=True, tessdata=find_tessdata())
                self.assertTrue(rects, "OCR search hit must have visible PDF coordinates")


if __name__=="__main__":
    unittest.main()
