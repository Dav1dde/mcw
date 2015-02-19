$(document).ready(function() {
    /*
    $('.console').resizable({
        handles: 's',
        stop: function(event, ui) {
            $(this).css("width", '');
        }
    });
    */

    var socket = io.connect('http://' + document.domain + ':' + location.port);

    socket.on('connect', function() {
        console.log('we did it reddit')
        socket.emit('connection', 'Yeah, I am here...')
    });

    socket.on('cm', function(data) {
        console.log(data)
        var color = ''
        if (data.type == 'stderr') {
            color = 'red'
        }

        $('.console').append($('<pre>').text(data.message).css('color', color))

    });
})