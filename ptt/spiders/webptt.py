# -*- coding: utf-8 -*-
import scrapy
import sys
import re

from datetime import datetime
from ptt.items import PostItem
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

# reload(sys)
# sys.setdefaultencoding('utf-8')

# class WebpttSpider(scrapy.Spider):
class WebpttSpider(CrawlSpider):
    name = "webptt"
    allowed_domains = ["www.ptt.cc"]
    ptt_url = 'https://www.ptt.cc'
    start_urls = ['https://www.ptt.cc/bbs/Gossiping/index.html']
    MAX_PAGE = 5
    _page = 1

    rules = (
        Rule(LinkExtractor(allow=('M\.\d+'), ), callback='parse_article', process_request='add_cookie'),
        # Rule(LinkExtractor(allow=('/bbs/\w+/index\.html')), callback='parse_list', process_request='add_cookie'),
        # Rule(LinkExtractor(allow=('M\.\d+')), callback='parse_article', follow=True, process_request='add_cookie'),
    )

    def add_cookie(self, request):
        request.cookies['over18'] = 1
        return request

    def start_requests(self):
        for i, url in enumerate(self.start_urls):
            yield scrapy.Request(url, cookies={'over18':'1'}, callback=self.parse_list)

    def parse_list(self, response):
        # Get topic string
        topic = response.url.split('/')[-2]

        if topic is not None:
            page = re.search(r'href="/bbs/' + topic + '/index(\d+).html">&lsaquo;', response.text)
            last_page = 1;
            if page is not None:
                last_page = int(page.group(1))

            i = 0
            while i < self.MAX_PAGE:
                url = self.ptt_url + '/bbs/' + topic + '/index' + str(last_page) + '.html'
                yield scrapy.Request(url, cookies={'over18':'1'})
                last_page = last_page - 1
                i = i + 1

        for div in response.css('div.r-ent'):
            try:
                # ex. link would be <a href="/bbs/PublicServan/M.1127742013.A.240.html">Re: [問題] 職等</a>
                href = div.css('a::attr(href)').extract_first()
                url = self.ptt_url + href
                yield scrapy.Request(url, cookies={'over18':'1'}, callback=self.parse_article)
            except:
                pass
        pass

    def parse_article(self, response):
        item = PostItem()
        item['title'] = response.xpath(
            '//meta[@property="og:title"]/@content')[0].extract()
        item['author'] = response.xpath(
            '//div[@class="article-metaline"]/span[text()="作者"]/following-sibling::span[1]/text()')[
                0].extract().split(' ')[0]
        datetime_str = response.xpath(
            '//div[@class="article-metaline"]/span[text()="時間"]/following-sibling::span[1]/text()')[
                0].extract()
        item['date'] = datetime.strptime(datetime_str, '%a %b %d %H:%M:%S %Y')

        item['content'] = response.xpath('//div[@id="main-content"]/text()')[
            0].extract()

        comments = []
        total_score = 0
        for comment in response.xpath('//div[@class="push"]'):
            push_tag = comment.css('span.push-tag::text')[0].extract()
            push_user = comment.css('span.push-userid::text')[0].extract()
            push_content = comment.css('span.push-content::text')[0].extract()

            if '推' in push_tag:
                score = 1
            elif '噓' in push_tag:
                score = -1
            else:
                score = 0

            total_score += score

            comments.append({'user': push_user,
                             'content': push_content,
                             'score': score})

        item['comments'] = comments
        item['score'] = total_score
        item['url'] = response.url

        yield item
