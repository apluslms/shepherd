
var socket = io.connect('http://' + document.domain + ':' + 5001);
    socket.on('update', function(data) {
        console.log(data)
        $("#"+data.course_id+".table-number").html(data.build_number);
        $("#"+data.course_id+".table-step").html(data.current_step);
        if (data.current_state !== null) {
            $("#" + data.course_id + ".table-state").html(data.current_state);
        }
        if (data.roman_step === null) {
            $("#" + data.course_id + ".table-roman-step").html("Not Running");
        } else {
            $("#" + data.course_id + ".table-roman-step").html("Running Step " + data.roman_step);
        }

    });
        socket.on('connect', function() {
      console.log('connect')
    });
