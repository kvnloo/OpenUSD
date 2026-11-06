#!/pxrpythonsubst
#
# Copyright 2018 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.

import os
import unittest
import zipfile

from pxr import Sdf

class TestSdfZipFile(unittest.TestCase):
    def _ValidateSourceAndZippedFile(self, srcFile, zipFile, fileInZip, 
                                     fixLineEndings=False):
        with open(srcFile, "rb") as f:
            srcData = bytearray(f.read())
            if fixLineEndings:
                srcData = srcData.replace("\r\n".encode("utf-8"),
                                          "\n".encode("utf-8"))

        if isinstance(zipFile, Sdf.ZipFile):
            self.assertEqual(
                srcData, zipFile.GetFile(fileInZip))
        elif isinstance(zipFile, zipfile.ZipFile):
            self.assertEqual(srcData, zipFile.read(fileInZip))

    def test_Reader(self):
        """Test Sdf.ZipFileReader"""
        zf = Sdf.ZipFile.Open("nonexistent.usdz")
        self.assertIsNone(zf)

        zf = Sdf.ZipFile.Open("test_reader.usdz")
        self.assertTrue(zf)
        self.assertEqual(
            zf.GetFileNames(), ["a.test", "b.png", "sub/c.png", "sub/d.txt"])

        self.assertIsNone(zf.GetFile("nonexistent.txt"))
        self.assertIsNone(zf.GetFileInfo("nonexistent.txt"))

        # test_reader.usdz was created with text files with Unix-style
        # line endings. Fix up line endings in the baseline files to
        # accommodate this, in case those files had line ending
        # translations applied.
        fixLineEndings = True

        fileInfo = zf.GetFileInfo("a.test")
        self.assertEqual(fileInfo.dataOffset, 64)
        self.assertEqual(fileInfo.size, 83)
        self.assertEqual(fileInfo.uncompressedSize, 83)
        self.assertEqual(fileInfo.crc, 2187659876)
        self.assertEqual(fileInfo.compressionMethod, 0)
        self.assertFalse(fileInfo.encrypted)
        self._ValidateSourceAndZippedFile(
            "src/a.test", zf, "a.test", fixLineEndings)

        fileInfo = zf.GetFileInfo("b.png")
        self.assertEqual(fileInfo.dataOffset, 192)
        self.assertEqual(fileInfo.size, 7228)
        self.assertEqual(fileInfo.uncompressedSize, 7228)
        self.assertEqual(fileInfo.crc, 384784137)
        self.assertEqual(fileInfo.compressionMethod, 0)
        self.assertFalse(fileInfo.encrypted)
        self._ValidateSourceAndZippedFile("src/b.png", zf, "b.png")

        fileInfo = zf.GetFileInfo("sub/c.png")
        self.assertEqual(fileInfo.dataOffset, 7488)
        self.assertEqual(fileInfo.size, 6139)
        self.assertEqual(fileInfo.uncompressedSize, 6139)
        self.assertEqual(fileInfo.crc, 2488450460)
        self.assertEqual(fileInfo.compressionMethod, 0)
        self.assertFalse(fileInfo.encrypted)
        self._ValidateSourceAndZippedFile("src/sub/c.png", zf, "sub/c.png")

        fileInfo = zf.GetFileInfo("sub/d.txt")
        self.assertEqual(fileInfo.dataOffset, 13696)
        self.assertEqual(fileInfo.size, 87)
        self.assertEqual(fileInfo.uncompressedSize, 87)
        self.assertEqual(fileInfo.crc, 2546026356)
        self.assertEqual(fileInfo.compressionMethod, 0)
        self.assertFalse(fileInfo.encrypted)
        self._ValidateSourceAndZippedFile(
            "src/sub/d.txt", zf, "sub/d.txt", fixLineEndings)
        
    def test_Writer(self):
        """Test Sdf.ZipFileWriter"""
        if os.path.isfile("test_writer.usdz"):
            os.remove("test_writer.usdz")

        with Sdf.ZipFileWriter.CreateNew("test_writer.usdz") as zfw:
            self.assertTrue(zfw)

            # Zip file should not be created until Save() is called on file
            # writer or the writer is destroyed.
            self.assertFalse(os.path.isfile("test_writer.usdz"))
            
            addedFile = zfw.AddFile("src/a.test")
            self.assertEqual(addedFile, "src/a.test")

            addedFile = zfw.AddFile("src/b.png", "b.png")
            self.assertEqual(addedFile, "b.png")

        self.assertTrue(os.path.isfile("test_writer.usdz"))
        
        # Verify that the zip file can be read by Sdf.ZipFile.
        zf = Sdf.ZipFile.Open("test_writer.usdz")
        self.assertEqual(zf.GetFileNames(), ["src/a.test", "b.png"])

        # Since we're writing files into a .usdz and then extracting
        # and comparing them to the original file, we don't need to
        # do any line ending fix-ups.
        dontFixLineEndings = False

        def _GetFileSize(file):
            return os.stat(file).st_size

        def _ComputeCRC(file):
            import zlib
            with open(file, "rb") as f:
                return zlib.crc32(f.read())

        fileInfo = zf.GetFileInfo("src/a.test")
        self.assertEqual(fileInfo.dataOffset, 64)
        self.assertEqual(fileInfo.size, _GetFileSize("src/a.test"))
        self.assertEqual(fileInfo.uncompressedSize, _GetFileSize("src/a.test"))
        self.assertEqual(fileInfo.crc, _ComputeCRC("src/a.test"))
        self.assertEqual(fileInfo.compressionMethod, 0)
        self.assertFalse(fileInfo.encrypted)

        fileInfo = zf.GetFileInfo("b.png")
        self.assertEqual(fileInfo.dataOffset, 192)
        self.assertEqual(fileInfo.size, 7228)
        self.assertEqual(fileInfo.uncompressedSize, 7228)
        self.assertEqual(fileInfo.crc, 384784137)
        self.assertEqual(fileInfo.compressionMethod, 0)
        self.assertFalse(fileInfo.encrypted)

        self._ValidateSourceAndZippedFile(
            "src/a.test", zf, "src/a.test", dontFixLineEndings)
        self._ValidateSourceAndZippedFile("src/b.png", zf, "b.png")

        # Verify that the data offset for all files in the archive are
        # aligned on 64-byte boundaries.
        for f in zf.GetFileNames():
            self.assertEqual(zf.GetFileInfo(f).dataOffset % 64, 0)

        # Verify that zip file can be read by third-party zip libraries
        # (in this case, Python's zip module)
        zf = zipfile.ZipFile("test_writer.usdz")
        self.assertEqual(zf.namelist(), ["src/a.test", "b.png"])
        self.assertIsNone(zf.testzip())

        self._ValidateSourceAndZippedFile(
            "src/a.test", zf, "src/a.test", dontFixLineEndings)
        self._ValidateSourceAndZippedFile("src/b.png", zf, "b.png")

    def test_WriterAlignment(self):
        """Test that Sdf.ZipFileWriter writes files so that they're aligned
        according to the .usdz specification"""
        with open("test_align_2.txt", "wb") as f:
            f.write("This is a test file".encode("utf-8"))

        # Create .usdz files with two files, where the size of the first file 
        # varies from 1 byte to 64 bytes, then verify that the second file's 
        # data is aligned to 64 bytes.
        for i in range(1, 65):
            with open("test_align_1.txt", "wb") as f:
                f.write(("a" * i).encode("utf-8"))

            with Sdf.ZipFileWriter.CreateNew("test_align.usdz") as zfw:
                zfw.AddFile("test_align_1.txt")
                zfw.AddFile("test_align_2.txt")
            
            zf = Sdf.ZipFile.Open("test_align.usdz")
            fi = zf.GetFileInfo("test_align_1.txt")
            self.assertEqual(fi.dataOffset % 64, 0)

            fi = zf.GetFileInfo("test_align_2.txt")
            self.assertEqual(fi.dataOffset % 64, 0)
            
    def test_WriterUtf8Filename(self):
        """Test that Sdf.ZipFileWriter sets the UTF-8 filename flag (bit 11)
        for non-ASCII file names and leaves it unset for ASCII names"""
        if os.path.isfile("test_utf8.usdz"):
            os.remove("test_utf8.usdz")

        utf8Name = "blåbær/rødgrød.test"
        with Sdf.ZipFileWriter.CreateNew("test_utf8.usdz") as zfw:
            self.assertTrue(zfw)

            addedFile = zfw.AddFile("src/a.test", utf8Name)
            self.assertEqual(addedFile, utf8Name)

            addedFile = zfw.AddFile("src/a.test", "ascii.test")
            self.assertEqual(addedFile, "ascii.test")

        self.assertTrue(os.path.isfile("test_utf8.usdz"))

        # Verify that the zip file can be read by Sdf.ZipFile.
        zf = Sdf.ZipFile.Open("test_utf8.usdz")
        self.assertEqual(zf.GetFileNames(), [utf8Name, "ascii.test"])
        self._ValidateSourceAndZippedFile("src/a.test", zf, utf8Name)
        self._ValidateSourceAndZippedFile("src/a.test", zf, "ascii.test")

        # Multi-byte names must not break 64-byte data alignment.
        for f in zf.GetFileNames():
            self.assertEqual(zf.GetFileInfo(f).dataOffset % 64, 0)

        # Python's zip module decodes names as UTF-8 only if bit 11 is set.
        zf = zipfile.ZipFile("test_utf8.usdz")
        self.assertEqual(zf.namelist(), [utf8Name, "ascii.test"])
        self.assertIsNone(zf.testzip())
        self.assertTrue(zf.getinfo(utf8Name).flag_bits & 0x800)
        self.assertFalse(zf.getinfo("ascii.test").flag_bits & 0x800)
        self._ValidateSourceAndZippedFile("src/a.test", zf, utf8Name)
        self._ValidateSourceAndZippedFile("src/a.test", zf, "ascii.test")

    def test_WriterUtf8ReviewInteropAndAlignment(self):
        output = "test_utf8_review_interop.usdz"
        names = ("ascii.test", "blåbær/rødgrød.test",
                 "こんにちは.usd")
        bits = (0, 0x0800, 0x0800)
        if os.path.isfile(output):
            os.remove(output)

        with Sdf.ZipFileWriter.CreateNew(output) as writer:
            self.assertTrue(writer)
            for name in names:
                self.assertEqual(
                    writer.AddFile("src/a.test", name), name)

        with zipfile.ZipFile(output, "r") as archive:
            self.assertEqual(archive.namelist(), list(names))
            self.assertIsNone(archive.testzip())
            for name, expectedBits in zip(names, bits):
                self.assertEqual(
                    archive.getinfo(name).flag_bits, expectedBits)
                self._ValidateSourceAndZippedFile(
                    "src/a.test", archive, name)

        usdArchive = Sdf.ZipFile.Open(output)
        self.assertTrue(usdArchive)
        self.assertEqual(usdArchive.GetFileNames(), list(names))
        for name in names:
            self.assertEqual(
                usdArchive.GetFileInfo(name).dataOffset % 64, 0)
            self._ValidateSourceAndZippedFile(
                "src/a.test", usdArchive, name)

    def test_WriterUtf8ReviewLocalAndCentralFlags(self):
        output = "test_utf8_review_headers.usdz"
        names = ("ascii.test", "blåbær/rødgrød.test",
                 "こんにちは.usd")
        bits = (0, 0x0800, 0x0800)
        byteLengths = (10, 23, 19)
        if os.path.isfile(output):
            os.remove(output)

        with Sdf.ZipFileWriter.CreateNew(output) as writer:
            self.assertTrue(writer)
            for name in names:
                self.assertEqual(
                    writer.AddFile("src/a.test", name), name)

        with open(output, "rb") as stream:
            raw = stream.read()
        end = raw.rfind(b"PK\x05\x06")
        self.assertEqual(end, len(raw) - 22)
        self.assertEqual(
            int.from_bytes(raw[end + 10:end + 12], "little"),
            len(names))
        cursor = int.from_bytes(
            raw[end + 16:end + 20], "little")

        for name, expectedBits, expectedLength in zip(
                names, bits, byteLengths):
            encoded = name.encode("utf-8")
            self.assertEqual(len(encoded), expectedLength)
            self.assertEqual(raw[cursor:cursor + 4], b"PK\x01\x02")
            self.assertEqual(
                int.from_bytes(raw[cursor + 8:cursor + 10],
                               "little"),
                expectedBits)
            filenameLength = int.from_bytes(
                raw[cursor + 28:cursor + 30], "little")
            extraLength = int.from_bytes(
                raw[cursor + 30:cursor + 32], "little")
            commentLength = int.from_bytes(
                raw[cursor + 32:cursor + 34], "little")
            local = int.from_bytes(
                raw[cursor + 42:cursor + 46], "little")
            self.assertEqual(filenameLength, expectedLength)
            self.assertEqual(
                raw[cursor + 46:cursor + 46 + filenameLength],
                encoded)
            self.assertEqual(raw[local:local + 4], b"PK\x03\x04")
            self.assertEqual(
                int.from_bytes(raw[local + 6:local + 8],
                               "little"),
                expectedBits)
            self.assertEqual(
                int.from_bytes(raw[local + 26:local + 28],
                               "little"),
                expectedLength)
            self.assertEqual(
                raw[local + 30:local + 30 + expectedLength],
                encoded)
            cursor += 46 + filenameLength + extraLength + commentLength

        self.assertEqual(cursor, end)

    def test_WriterDiscard(self):
        if os.path.isfile("test_discard.usdz"):
            os.remove("test_discard.usdz")

        with Sdf.ZipFileWriter.CreateNew("test_discard.usdz") as zfw:
            self.assertTrue(zfw)
        
            # Zip file should not be written if Discard() is called.
            zfw.Discard()
            self.assertFalse(os.path.isfile("test_discard.usdz"))

        self.assertFalse(os.path.isfile("test_discard.usdz"))

    def test_WriterEmptyArchive(self):
        """Test corner case writing an empty zip archive with 
        Sdf.ZipFileWriter"""
        if os.path.isfile("empty.usdz"):
            os.remove("empty.usdz")

        with Sdf.ZipFileWriter.CreateNew("empty.usdz"):
            pass
        self.assertTrue(os.path.isfile("empty.usdz"))

        # Verify that zip file can be read by Sdf.ZipFile
        zf = Sdf.ZipFile.Open("empty.usdz")
        self.assertTrue(zf)
        self.assertEqual(zf.GetFileNames(), [])

        # Verify that zip file can be read by third-party zip libraries
        # (in this case, Python's zip module)
        zf = zipfile.ZipFile("empty.usdz")
        self.assertIsNone(zf.testzip())
        self.assertEqual(zf.namelist(), [])

if __name__ == "__main__":
    unittest.main()

