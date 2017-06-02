(function () {
    var PENDING_CLASS = 'documentfusion-status-in_progress';

    $(document).ready(function () {
        $('.documentfusion-refresh').click(generateDocument);
        $('.documentfusion-viewlet-download').each(function () {
            var viewlet = $(this);
            if (viewlet.hasClass(PENDING_CLASS)) {
                var viewletId = viewlet.attr('id');
                pollForGenerationFinished(viewletId);
            }
        })
    });

    function generateDocument(evt) {
        evt.preventDefault();
        var button = $(this);
        var viewletId = button.parents('.documentfusion-viewlet').attr('id');
        var url = button.data().url;
        var data = {'ajax_load': 1};
        var pdf = button.data().pdf;
        if (pdf !== undefined) {
            data['pdf'] = pdf.toString();
        }
        var conversionName = conversionNameFromId(viewletId);
        if (conversionName) {
            data.conversion = conversionName;
        }
        $.post(url, data, function (html) {
            updateViewlet(viewletId, html);
        });
    }

    function updateViewlet(viewletId, html) {
        $('#' + viewletId).replaceWith(html);
        if ($(html).hasClass(PENDING_CLASS)) {
            pollForGenerationFinished(viewletId);
        }
        $('#' + viewletId + ' button.documentfusion-refresh')
            .unbind('click')
            .click(generateDocument)
    }

    function pollForGenerationFinished(viewletId) {
        var checkStatusInterval = setInterval(function () {
            $.post('documentfusion-status', {
                ajax_load: 1,
                conversion: conversionNameFromId(viewletId)
            }).then(function (html) {
                if (!$(html).hasClass(PENDING_CLASS)) {
                    clearInterval(checkStatusInterval);
                    updateViewlet(viewletId, html);
                }
            });
        }, 2500);
    }

    function conversionNameFromId(viewletId) {
        if (viewletId === 'documentfusion-viewlet') {
            return '';
        } else {
            return viewletId.substr('documentfusion-viewlet-'.length);
        }
    }

}());
