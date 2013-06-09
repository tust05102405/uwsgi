#!./uwsgi --http-socket :9090 --async 100 ...
# same chat example but using uwsgi async api
import uwsgi
import time
import redis

def application(env, sr):

    ws_scheme = 'ws'
    if 'HTTPS' in env or env['wsgi.url_scheme'] == 'https':
        ws_scheme = 'wss'

    if env['PATH_INFO'] == '/':
        sr('200 OK', [('Content-Type','text/html')])
        return """
    <html>
      <head>
          <script language="Javascript">
            var s = new WebSocket("%s://%s/foobar/");
            s.onopen = function() {
              alert("connected !!!");
              s.send("ciao");
            };
            s.onmessage = function(e) {
		var bb = document.getElementById('blackboard')
		var html = bb.innerHTML;
		bb.innerHTML = html + '<br/>' + e.data;
            };

	    s.onerror = function(e) {
			alert(e);
		}

	s.onclose = function(e) {
		alert("connection closed");
	}

            function invia() {
              var value = document.getElementById('testo').value;
              s.send(value);
            }
          </script>
     </head>
    <body>
        <h1>WebSocket</h1>
        <input type="text" id="testo"/>
        <input type="button" value="invia" onClick="invia();"/>
	<div id="blackboard" style="width:640px;height:480px;background-color:black;color:white;border: solid 2px red;overflow:auto">
	</div>
    </body>
    </html>
        """ % (ws_scheme, env['HTTP_HOST'])
    elif env['PATH_INFO'] == '/favicon.ico':
        return ""
    elif env['PATH_INFO'] == '/foobar/':
	uwsgi.websocket_handshake(env['HTTP_SEC_WEBSOCKET_KEY'], env.get('HTTP_ORIGIN', ''))
        print "websockets..."
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        channel = r.pubsub()
        channel.subscribe('foobar')

        websocket_fd = uwsgi.connection_fd()
        redis_fd = channel.connection._sock.fileno()
        
        while True:
            uwsgi.wait_fd_read(websocket_fd)
            uwsgi.wait_fd_read(redis_fd)
            uwsgi.suspend()
            fd = uwsgi.ready_fd()
            if fd > -1:
                if fd == websocket_fd:
                    msg = uwsgi.websocket_recv_nb()
                    if msg:
                        r.publish('foobar', msg)
                elif fd == redis_fd:
                    msg = channel.parse_response() 
                    # only interested in user messages
                    if msg[0] == 'message':
                        uwsgi.websocket_send("[%s] %s" % (time.time(), msg))
