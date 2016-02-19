(function($) {
  $(document).on('ready', function() {
    $('select[name="action"]', '#changelist-form').on('change', function() {
      if ($(this).val() == 'export_admin_action') {
        $('select[name="file_format"]', '#changelist-form').parent().show();
      } else {
        $('select[name="file_format"]', '#changelist-form').parent().hide();
      }
    });
    $('select[name="action"]', '#changelist-form').change();
  });
})(django.jQuery);
