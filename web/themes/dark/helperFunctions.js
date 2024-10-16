/**
 * helper functions for setup-pages
 *
 * @author Michael Ortenstein
 */

function updateLabel(elementId) {
    /** @function updateLabel
     * sets the value-label (if exists) attached to the element to the element value
     * @param {string} elementId - the id of the element
     * @requires class:valueLabel assigned to the attached label
     */
    var element = $('#' + $.escapeSelector(elementId));
    var label = $('label[for="' + elementId + '"].valueLabel');
    if ( label.length == 1 ) {
        var suffix = label.attr('suffix');
        var text = parseFloat(element.val()).toLocaleString(undefined, {maximumFractionDigits: 2});
        if ( suffix != '' ) {
            text += ' ' + suffix;
        }
        label.text(text);
    }
}

function setInputValue(elementId, value) {
    /** @function setInputValue
     * sets the value-label (if exists) attached to the element to the element value
     * @param {string} elementId - the id of the element
     * @param {string} value - the value the element has to be set to
     * if the element has data-attribute 'signcheckbox' the checkbox with the id of the attribute
     * will represent negative numbers by being checked
     */
    if ( !isNaN(value) ) {
        var element = $('#' + $.escapeSelector(elementId));
        var signCheckboxName = element.data('signcheckbox');
        var signCheckbox = $('#' + signCheckboxName);
        if ( signCheckbox.length == 1 ) {
            // checkbox exists
            if ( value < 0 ) {
                signCheckbox.prop('checked', true);
                value *= -1;
            } else {
                signCheckbox.prop('checked', false);
            }
        }
        element.val(value);
        if ( element.attr('type') == 'range' ) {
            updateLabel(elementId);
        }
    }
}

function setInputText(elementId, value) {
  /** @function setInputText
   * sets the value-label (if exists) attached to the element to the given value
   **/
  var element = $('#' + $.escapeSelector(elementId));
  element.text(value);
}

function setInputText(elementId, value) {
  /** @function setInputText
   * sets the value-label (if exists) attached to the element to the given value
   **/
  var element = $('#' + $.escapeSelector(elementId));
  element.text(value);
}

function getTopicToSendTo (elementId) {
    var element = $('#' + $.escapeSelector(elementId));
    var topic = element.data('topicprefix') + elementId;
    topic = topic.replace('/get/', '/set/');
    return topic;
}

function setToggleBtnGroup(groupId, option) {
    /** @function setInputValue
     * sets the value-label (if exists) attached to the element to the element value
     * @param {string} elementId - the id of the button group
     * @param {string} option - the option the group btns will be set to
     * @requires
 data-attribute 'option' (unique for group) assigned to every radio-btn
     */
    $('input[name="' + groupId + '"][data-option="' + option + '"]').prop('checked', true);
    $('input[name="' + groupId + '"][data-option="' + option + '"]').closest('label').addClass('active');
    // and uncheck all others
    $('input[name="' + groupId + '"]').not('[data-option="' + option + '"]').each(function() {
        $(this).prop('checked', false);
        $(this).closest('label').removeClass('active');
    });
    chargeLimitationOptionsShowHide($('#' + $.escapeSelector(groupId)), option)
}
