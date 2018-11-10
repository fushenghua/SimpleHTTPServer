"""Simple HTTP Server.
This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.
"""


__version__ = "0.6"

__all__ = ["SimpleHTTPRequestHandler"]

import os
import posixpath
import BaseHTTPServer
import urllib
import cgi
import sys
import shutil
import mimetypes
import json
import re
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class SimpleHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    """Simple HTTP request handler with GET and HEAD commands.
    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method.
    The GET and HEAD requests are identical except that the HEAD
    request omits the actual contents of the file.
    """

    server_version = "SimpleHTTP/" + __version__

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

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
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
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
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

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
        rootPath = os.path.dirname(os.path.abspath(__file__))
        config = open(rootPath+"/config.json")
        
        setting = json.load(config)
        projectName= setting["name"]
        strinfo = re.compile('projectName')
        head = open(rootPath+"/static/head.html") 
        footer = open(rootPath+"/static/footer.html") 
        for line in head.readlines(): 
            b = strinfo.sub(projectName,line)
            f.write(b)
        head.close

        prePath= "/"
        f.write('<li class="breadcrumb-item"><i class="fa fa-folder-open"> </i><a href="%s">%s</a></li>'% (prePath," root "))
        for prePath2 in self.splitPath(displaypath):
            if prePath2.strip():
                prePath=prePath+prePath2+"/"
                print prePath
                f.write('<li class="breadcrumb-item"><a href="%s">%s </a></li>'% (prePath,prePath2))   
        f.write("</ol>\n")

        # f.write('<div class="row"><ul class="fa-ul">\n')
        f.write('<div class="row">\n')
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            icon='<span class="fa-li"><i class="fa fa-file-o"></i></span>'
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
                icon='<span class="fa-li"><i class="fa fa-folder"></i></span>'
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            if "apk" in fullname:   
                icon='<span class="fa-li"><i class="fa fa-android fa-xs"></i></span>' 
            if "html" in fullname:
                icon= '<span class="fa-li"><i class="fa fa-html5 fa-xs"></i></span>' 
            if "py" in fullname or "java" in fullname:
                icon='<span class="fa-li"><i class="fa fa-file-code-o"></i></span>'  

            f.write('<div class="col-md-6"><li>%s<a href="%s">%s</a> </div></li>\n'
                    % (icon,urllib.quote(linkname), cgi.escape(displayname)))  
            f.write('<div class="col-md-2">.col-md-4</div>')
            f.write('<div class="col-md-2">.col-md-4</div>')  
            f.write('<div class="col-md-2">.col-md-4</div>')  
            f.write('<div class="col-md-2">.col-md-4</div>')            
                    
        # f.write("</ul>")
        f.write("</div>")
        for line in footer.readlines(): 
                b = strinfo.sub(projectName,line)
                f.write(b)   
        footer.close()

        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def splitPath(self,path):
        return path.split("/")

    def getRootPath(self):
        rootPath = os.path.dirname(os.path.abspath(__file__))
        return rootPath

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.
        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)
        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
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


def test(HandlerClass = SimpleHTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer):
    BaseHTTPServer.test(HandlerClass, ServerClass)


if __name__ == '__main__':
    test()
    # print("/.git/refs/remotes/origin/".split("/"))