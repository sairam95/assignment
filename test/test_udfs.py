from glue_jobs.search_revenue_glue_job import extract_domains, extract_search_keyword


def test_extract_domain():
    test_domain_urls = [("https://www.google.com/search?q=adobe", "google.com"),
                        ("https://www.adobe.com/creativecloud.html", "adobe.com"),
                        ("https://www.github.com/sairam95/assignment", "github.com")]

    is_domain_extracted = [extract_domains(url) == expected for url, expected in test_domain_urls]
    assert all(is_domain_extracted)


def test_extract_search_keyword():
    test_search_keywords = [("https://www.google.com/search?q=adobe", "adobe"),
                        ("https://www.bing.com/search?q=grammys+2022&qs=PN&sc=8-0&cvid"
                         "=D123D62D4F9A43C8AA9565CA53B5FBBC&FORM=QBLH&sp=1", "grammys 2022"),
                        ("https://search.yahoo.com/search?p=stock+market&fr=yfp-t&fr2=p%3Afp%2Cm%3Asb&ei=UTF-8&fp=1",
                         "stock market")]

    is_search_keyword_extracted = [extract_search_keyword(url) == expected for url, expected in test_search_keywords]
    assert all(is_search_keyword_extracted)
