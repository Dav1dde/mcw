$(document).ready(function() {
    $('body main section footer aside').remove()
    $('#password').focus()

    $('#password').keyup(function(event) {
        $('body main section footer').text('')

        if (event.keyCode == 13) {  // enter
            $.post('/login', {'password': $('#password').val()}, function(data) {
                if (data.success) { // we logged in
                    location.reload(true)
                } else { // wrong password most likely
                    $('body main section footer').text(data.error)
                }
            }, 'json')
        }
    })
})