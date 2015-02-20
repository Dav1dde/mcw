function isAtBottom(element) {
    element = $(element)
    return element.innerHeight() + element.scrollTop() >= element[0].scrollHeight
}

String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

jQuery.fn.extend({
    setStatus: function(type, text) {
        this.children('.status').text(text)
        return this.removeClass(
            'label-default label-primary label-success label-info label-warning label-danger'
        ).addClass('label-'+type)
    }
})

function setServerStatus(data) {
    if (data.server_state == 'running') {
        $('.status-server').setStatus('success', 'Running')
    } else if (data.server_state == 'stopped') {
        $('.status-server').setStatus('danger', 'Stopped')
    } else {
        $('.status-server').setStatus('warning', data.server_state.capitalize())
    }
}

$(document).ready(function() {
    /*
    $('.console').resizable({
        handles: 's',
        stop: function(event, ui) {
            $(this).css('width', '');
        }
    });
    */

    var socket = io.connect('/main');
    socket.on('error', function() {
        console.error('Error:', arguments)
        $('.status-webpanel').setStatus('warning', 'Errors Occured')
    });
    socket.on('message', function() { console.log('Unhandled message:', arguments) });

    socket.on('connecting',       function() { $('.status-webpanel').setStatus('warning', 'Connecting')          })
    socket.on('reconnecting',     function() { $('.status-webpanel').setStatus('warning', 'Reconnecting')        })
    socket.on('connect_failed',   function() { $('.status-webpanel').setStatus('danger',  'Connection Failed')   })
    socket.on('reconnect_failed', function() { $('.status-webpanel').setStatus('danger',  'Reconnecting Failed') })
    socket.on('disconnect',       function() { $('.status-webpanel').setStatus('danger',  'Disconnected')        })

    socket.on('welcome', function(data) {
        $('.status-webpanel').setStatus('success', 'Connected')
        setServerStatus(data)
    });
    socket.on('server-state', setServerStatus)
    socket.on('console-message', function(data) {
        console.log(data)
        var color = ''
        if (data.type == 'stderr') {
            color = 'red'
        }

        var atBottom = isAtBottom('.console');

        $('.console').append($('<pre>').text(data.message).css('color', color))
        if (atBottom) {
            $('.console').scrollTop($('.console')[0].scrollHeight)
        }
    });


    $('.command-input').keyup(function(event) {
        if (event.keyCode == 13) {  // enter
            socket.emit('command', {command: $(this).val()})
            $(this).val('')
        }
    })


})