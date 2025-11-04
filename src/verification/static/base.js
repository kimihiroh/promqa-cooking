$(document).ready(function () {

    // Initialize Plyr
    const player = new Plyr('#player', {
        debug: true,
        controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume', 'settings', 'fullscreen'],
        settings: ['quality', 'speed'],
        quality: {
            default: 360,
            options: [360, 2160],
            forced: true,
            onChange: (quality) => {
                switchQuality(quality);
                console.log('Switched to quality:', quality);
            },
        }
    });
    player.on('ready', event => {
        const instance = event.detail.plyr;
        console.log('Plyr is ready', instance);
    });

    // Function to switch video quality
    function switchQuality(quality) {
        const video = document.getElementById('player');
        const sources = video.getElementsByTagName('source');

        for (let i = 0; i < sources.length; i++) {
            if (sources[i].getAttribute('data-quality') == quality) {
                video.src = sources[i].getAttribute('src');
                video.load();
                break;
            }
        }};


    /* Validate responses before submission */
    $("#submitButton").click(function (e) {

        // check if verification is done
        let isQuestionUnchecked = false;
        let message = "Okay";
        let isAnyAnswerUnchecked = false;

        const val = $("input:radio[name='judge_q']:checked").val();
        if (val === undefined) {
            isQuestionUnchecked = true;
            message = "Check the question";
        } else if (val === 'true') {
            // as question is valid, now check its answer(s)
            for (let aid = 1; aid < 6; aid++) {
                // check if this answer element is not empty, i.e., need to check
                if(!$("#answer_value"+aid).is(':empty')) {
                    if (
                        $("input:radio[name='judge_a"+aid+"']:checked").val() === undefined
                    ) {
                        isAnyAnswerUnchecked = true;
                        message = "Check answer "+aid+".";
                        break;
                    }
                }
            }
        }

        // check if this is the last example
        let isLast = false;
        if ( $("#total_num").text() === $("#current_id").text() ){
            isLast = true;
        }

        // return message
        if (isQuestionUnchecked || isAnyAnswerUnchecked) {
            // handle error
            $("#alert-box")
                .empty()
                .append($("<strong>").text("Error: "))
                .append(message)
                .show();
            setTimeout(function() {
                window.scrollTo(0, 0);
            }, 100);
            e.preventDefault();
            return false;
        } else {
            if (isLast) {
                $("#alert-box")
                    .empty()
                    .append($("<strong>").text("You've completed!! Congrats!!"))
                    .show();
                setTimeout(function() {
                    window.scrollTo(0, 0);
                }, 100);
                setTimeout(function() {
                    $("form").submit();
                }, 3000);

                // Prevent immediate submission
                e.preventDefault();
                return false;
            }
        }
    });

    /* show answers when the question is valid when selected */
    $('input[name="judge_q"]').on('change', function () {
        if ($('#judge_q_true').is(':checked')) {
            $('#answers').show();
        } else {
            $('#answers').hide();
        }
    });
    /* show answers when the question is valid when loaded */
    let val = $("input:radio[name='judge_q']:checked").val();
        if (val !== undefined) {
            if ($('#judge_q_true').is(':checked')) {
                $('#answers').show();
            } else {
                $('#answers').hide();
            }
        }

    /* hide empty answer blocks */
    for (let aid = 1; aid < 6; aid++) {
        $('#answer_value'+aid).each(function() {
            if ($(this).is(':empty')) {
                $('#answer_box'+aid).hide();
            }
        });
    }
});
