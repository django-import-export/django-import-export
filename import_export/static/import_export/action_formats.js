(function ($) {
    $(document).ready(function () {
        var $actionsSelect, $formatsElement;
        $actionsSelect = $('.actions select[name="action"]');
        $formatsElement = $('.actions select[name="file_format"]');
        if ($('body').hasClass('grp-change-list')) {
            // using grappelli
            $ShowElementToShow = $formatsElement;
        } else {
            // using default admin
            $formatsElementToShow = $formatsElement.parent();
        }
        for (let i = 0; i < $actionsSelect.length; i++) {
            $actionsSelect.eq(i).change(function () {
                if ($(this).val() === 'export_admin_action') {
                    $formatsElementToShow.eq(i).show();
                } else {
                    $formatsElementToShow.eq(i).hide();
                }
            });
            $actionsSelect.eq(i).change();

            $formatsElement.eq(i).change(function () {
                for (let j = 0; j < $formatsElement.length; j++) {
                    if ($formatsElement.eq(j).val() != $(this).val()) {
                        $formatsElement.eq(j).val($(this).val());
                    }
                }
            });
        }
    });
})(django.jQuery);
