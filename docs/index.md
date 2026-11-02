# BHMarketer Crypto Press Release FAQ Generator

A searchable database of 50 questions about the BHMarketer.ai Buy Crypto Press Release service, with a page FAQ section and FAQPage JSON-LD. Built by [BHMarketer.ai](https://bhmarketer.ai/crypto-press-release/).

## Install

```bash
npm install -g @bhmarketer-ai/crypto-press-release-faq-generator
# or
pip install git+https://github.com/bhmarketer-ai/BHMarketer-Crypto-Press-Release-FAQ-Generator.git
```

## Ask a question

```bash
cpr-faq ask how much does it cost
cpr-faq ask which outlets can publish it
cpr-faq show 11
```

## Most asked questions

```bash
cpr-faq top 10
```

Questions are ranked by BHMarketer.ai's estimate of how often each one is asked.

## Page FAQ section

```bash
cpr-faq html > faq-section.html   # one H2, an H3 per question, FAQPage JSON-LD
cpr-faq seo                       # page SEO settings
```

See the full [FAQ](faq.md).
