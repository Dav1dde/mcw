function isAtBottom(element) {
    element = $(element)
    return element.innerHeight() + element.scrollTop() >= element[0].scrollHeight
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

    var socket = io.connect('/console');
    socket.on('error', function() { console.error('Error:', arguments) });
    socket.on('message', function() { console.log('Unhandled message:', arguments) });

    console.log(socket)

    socket.on('connect', function() {
        console.log('Connected ...')
    });

    socket.on('welcome', function() {
        console.log('Welcomed by server')
    });

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

})