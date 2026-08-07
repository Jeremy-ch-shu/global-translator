from setuptools import setup, find_packages

setup(
    name="global-translator",
    version="1.0.0",
    author="Jeremy",                        
    author_email="jeremyshu123@outlook.com",     
    description="Windows全局翻译工具 - 支持屏幕取词、文档翻译、会议实时翻译",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Jeremy-ch-shu/global-translator",  
    license="MIT",
    packages=find_packages(),
    install_requires=[
        'PySide6>=6.5.0',
        'pytesseract>=0.3.10',
        'Pillow>=10.0.0',
        'mss>=9.0.0',
        'deep-translator>=1.11.0',
        'python-docx>=1.1.0',
        'PyMuPDF>=1.23.0',
        'faster-whisper>=0.10.0',
        'keyboard>=0.13.5',
        'pywin32>=306',
        'loguru>=0.7.2'
    ],
    entry_points={
        'console_scripts': [
            'global-translator=src.main:main',
        ],
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Multimedia :: Graphics :: Capture :: Screen Capture",
    ],
    keywords="translation ocr screen-capture document-translation live-caption",
    python_requires=">=3.10",
)