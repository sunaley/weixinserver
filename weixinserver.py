# -*- coding: utf-8 -*-

"""Simple HTTP Server.

This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.

"""


__version__ = "0.6"

__all__ = ["SimpleHTTPRequestHandler"]

from wechat_sdk import WechatConf
from wechat_sdk import WechatBasic
from wechat_sdk.exceptions import ParseError
from wechat_sdk.messages import *
from wechat_sdk.exceptions import OfficialAPIError
#from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
from io import open
import threading
import os
import posixpath
import BaseHTTPServer
import urllib
import urlparse
import cgi
import sys
import shutil
import mimetypes
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

def get_access_token_function():
    """ 注意返回值为一个 Tuple，第一个元素为 access_token 的值，第二个元素为 access_token_expires_at 的值 """
    out = ("","")
    try:
        with open("access_token.bin", mode="r", encoding="utf-8") as fin:
            out = tuple(fin.readline().encode("utf-8").split("&"))
            out = [i.rstrip("\n ") for i in out]
            if len(out) < 2:
                out = ("","")
            else:
                out[1] = int(out[1])
    except IOError:
        pass
    return out  # 此处通过你自己的方式获取 access_token

def set_access_token_function(access_token, access_token_expires_at):
    with open("access_token.bin", mode="w", encoding="utf-8") as fout:
        out = fout.write(access_token+u"&"+str(access_token_expires_at).decode("utf-8"))
        #print out
    #set_access_token_to_somewhere(access_token, access_token_expires_at)  # 此处通过你自己的方式设置 access_token

conf = WechatConf(
    token='', 
    appid='', 
    appsecret='', 
    encrypt_mode='compatible',  # 可选项：normal/compatible/safe，分别对应于 明文/兼容/安全 模式
    #encoding_aes_key=''  # 如果传入此值则必须保证同时传入 token, appid
    access_token_getfunc=get_access_token_function,
    access_token_setfunc=set_access_token_function,
)


wechat = WechatBasic(conf=conf)


class WechatMethod():
    signature = ""
    timestamp = ""
    nonce = ""
    echostr = ""
    log_massage = None
    def init_log_message(self,func):
        log_massage = func
    
    #def isinstance(self, wechat.message, "subscribe"):
    def CheckWechatServer(self, log_message, path):
        if "signature" in path and "timestamp" in path and "nonce" in path:
            query = urlparse.parse_qs(path[2:])
            try:
                self.signature = "".join(query["signature"])
                self.timestamp = "".join(query["timestamp"])
                self.nonce = "".join(query["nonce"])
                self.echostr = "".join(query["echostr"])
            except KeyError as e:
                print "POST Method"

            if wechat.check_signature(self.signature, self.timestamp, self.nonce):
                log_message("%s", "DDD")
                print 'Accept'
                return self.echostr if len(self.echostr)>0 else 'OK'
            else:
                print 'Wrong'
        return None
        
    def TypeBody(self, log_message, body_text):
        try:
            wechat.parse_data(body_text)
        except ParseError:
            print "Invalid Body Text"
        return wechat.message.type
        
    def DoMsgMethod(selfl, log_message):
        xml = ""
        if wechat.message.type == 'text':  
           #xml = wechat.response_text(content='谢谢您的指教，我们会持续增进公众号的内容。')
            xml = wechat.response_news()
            """if wechat.message.content == "测试".decode('utf-8'):
                content = "AABBCC測試".decode('utf-8')
                xml = wechat.response_text(content, escape=False)"""
        return xml
        
    def DoEventMethod(self, log_message):
        xml = ""
        #if isinstance(wechat.message, TextMessage)
        if wechat.message.type == 'subscribe':  # 关注事件(包括普通关注事件和扫描二维码造成的关注事件)
            self.log_message('%s', "Subscribe!")
            xml = wechat.response_text(content='您好！欢迎来到幸福微时代的公众号，很高兴见到您。')
            key = wechat.message.key                        # 对应于 XML 中的 EventKey (普通关注事件时此值为 None)
            ticket = wechat.message.ticket                  # 对应于 XML 中的 Ticket (普通关注事件时此值为 None)
        elif wechat.message.type == 'unsubscribe':  # 取消关注事件（无可用私有信息）
            pass
        elif wechat.message.type == 'scan':  # 用户已关注时的二维码扫描事件
            key = wechat.message.key                        # 对应于 XML 中的 EventKey
            ticket = wechat.message.ticket                  # 对应于 XML 中的 Ticket
        elif wechat.message.type == 'location':  # 上报地理位置事件
            latitude = wechat.message.latitude              # 对应于 XML 中的 Latitude
            longitude = wechat.message.longitude            # 对应于 XML 中的 Longitude
            precision = wechat.message.precision            # 对应于 XML 中的 Precision
        elif wechat.message.type == 'click':  # 自定义菜单点击事件
            key = wechat.message.key                        # 对应于 XML 中的 EventKey
            if key == "V1001_TODAY_NEWS":
                xml = wechat.response_news()
        elif wechat.message.type == 'view':  # 自定义菜单跳转链接事件
            key = wechat.message.key                        # 对应于 XML 中的 EventKey
        elif wechat.message.type == 'templatesendjobfinish':  # 模板消息事件
            status = wechat.message.status                  # 对应于 XML 中的 Status
        elif wechat.message.type in ['scancode_push', 'scancode_waitmsg', 'pic_sysphoto', 
                        'pic_photo_or_album', 'pic_weixin', 'location_select']:  # 其他事件
            key = wechat.message.key                        # 对应于 XML 中的 EventKey
        return xml
    #def ResponsesXML():
        
WechatC = WechatMethod()


class SimpleHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    """Simple HTTP request handler with GET and HEAD commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method.

    The GET and HEAD requests are identical except that the HEAD
    request omits the actual contents of the file.

    """
    
    server_version = "SimpleHTTP/" + __version__
    data = "测试!!!ABC"
    encoding = sys.getfilesystemencoding()
    signature = ""
    timestamp = ""
    nonce = ""
    echostr = ""
    Msgtype = ["text", "image", "voice", "video", "shortvideo", "link"] 
    Eventtype = ["subscribe", "shortvideo", "unsubscribe", "scan", "location", "click",
                 "view templatesendjobfinish", "scancode_push", "scancode_waitmsg", "pic_sysphoto", 
                 "pic_photo_or_album", "pic_weixin", "location_select"]
    
    
    def SendEmptyString(self):
        self.send_xmlheader(len(u'success'))
        self.wfile.write(u'success')
    
    def send_xmlheader(self,length):
        self.send_response(200)
        self.send_header("Content-type", "text/xml; charset=%s" % self.encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        
    def do_POST(self):
        """Serve a POST request."""
        ServerValid = WechatC.CheckWechatServer(self.log_message, self.path) #Check weixin server
        if not ServerValid:
            self.log_message('%s', "Not a weixin server.")
            return
            
        length = int(self.headers["Content-Length"])
        RecvieData = self.rfile.read(length).decode("utf-8") #Read Data
        XMLtype = WechatC.TypeBody(self.log_message, RecvieData) #Parse Data
        
        if not isinstance(wechat.message, EventMessage): #Data Type
            ResponseContent = WechatC.DoMsgMethod(self.log_message)
        elif XMLtype in self.Eventtype:
            ResponseContent = WechatC.DoEventMethod(self.log_message)
        
        if not ResponseContent: #if no content do nothing
            self.SendEmptyString()
            return
        ResponseContent = ResponseContent.encode('utf-8')
        self.send_xmlheader(len(ResponseContent))
        self.wfile.write(ResponseContent)
    
    def do_GET(self):
        """Serve a GET request."""
        
        ServerValid = WechatC.CheckWechatServer(self.log_message, self.path) #Check weixin server
        if ServerValid:
            self.send_xmlheader(len(ServerValid))
            self.wfile.write(ServerValid)
            return
        else:
            self.log_message('%s', "Not a weixin server.")

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urlparse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urlparse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        try:
            self.send_response(200)
            self.send_header("Content-type", ctype)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = StringIO()
        displaypath = cgi.escape(urllib.unquote(self.path))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
        f.write("<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s">%s</a>\n'
                    % (urllib.quote(linkname), cgi.escape(displayname)))
        f.write("</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        # Don't forget explicit trailing slash when normalizing. Issue17324
        trailing_slash = path.rstrip().endswith('/')
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path

    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)

    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init() # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream', # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        })

class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""

def test(HandlerClass = SimpleHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer):
    #BaseHTTPServer.test(HandlerClass, ServerClass)
    server = ThreadedHTTPServer(('0.0.0.0', 80), HandlerClass)
    print 'Starting server, use <Ctrl-C> to stop'
    server.serve_forever()
    

if __name__ == '__main__':
    """menu = {
    'button':[
        {
            'type': 'click',
            'name': '今日消息',
            'key': 'V1001_TODAY_NEWS'
        },
        {
            'type': 'click',
            'name': '歌手简介',
            'key': 'V1001_TODAY_SINGER'
        },
        {
            'name': '菜单',
            'sub_button': [
                {
                    'type': 'view',
                    'name': '搜索',
                    'url': 'http://www.soso.com/'
                },
                {
                    'type': 'view',
                    'name': '视频',
                    'url': 'http://v.qq.com/'
                },
                {
                    'type': 'click',
                    'name': '赞一下我们',
                    'key': 'V1001_GOOD'
                }
            ]
        }
    ]
}
    try:
        #wechat.delete_menu()
        $wechat.create_menu(menu)
    except OfficialAPIError:
        pass
    """
    test()
