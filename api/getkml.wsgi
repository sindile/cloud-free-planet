from webob import Request, Response
import datetime
from MappingCommon import MappingCommon

def buildSelect(mapc):
    select = '<select id="categLabel">\n'
    categMaxNum = int(mapc.getConfiguration("CategMaxNum"))
    categText = []
    categCode = []
    for ndx in range(1, categMaxNum + 1):
        categText = mapc.getConfiguration("CategText" + str(ndx))
        if categText is None:
            break
        categCode = mapc.getConfiguration("CategCode" + str(ndx))
        if categCode is None:
            categCode = categText
        select += "<option value='%s'>%s</option>\n" % (categCode, categText)
    select += "</select>\n"
    return select

def application(environ, start_response):
    req = Request(environ)
    res = Response()
    res.content_type = 'text/html'

    now = str(datetime.datetime.today())

    mapc = MappingCommon()
    logFilePath = mapc.projectRoot + "/log"
    kmlMapHeight = int(mapc.getConfiguration('KMLMapHeight'))
    apiUrl = mapc.getConfiguration('APIUrl')
    kmlGenScript = mapc.getConfiguration('KMLGenScript')
    mapUrl = mapc.getConfiguration('MapUrl')
    instructions = mapc.getConfiguration('KMLInstructions')
    kmlGenUrl = "%s/%s" % (apiUrl, kmlGenScript)

    k = open(logFilePath + "/OL.log", "a")
    k.write("\ngetkml: datetime = %s\n" % now)

    kmlName = req.params['kmlName']
    if len(kmlName) > 0:
        (kmlType, kmlTypeDescr) = mapc.getKmlType(kmlName)
        mapHint = mapc.querySingleValue("select hint from kml_data where name = '%s'" % kmlName)

        # Training and field mapping cases.
        # These have an assignmentId.
        try:
            assignmentId = req.params['assignmentId']
            resultsAccepted = req.params['resultsAccepted']
            submitTo = req.params['submitTo']
            csrfToken = req.params['csrfToken']
            workerId = ''
            target = '_parent'
            select = buildSelect(mapc)

            # Training case.
            # This has a tryNum.
            try:
                tryNum = req.params['tryNum']
                hitId = ''
                commentsDisabled = 'disabled'
                mapHint = '<div class="hints">Hint: %s</div>' % mapHint
                kmlMapHeight -= 30        # Reduce map height to leave room for hints.

            # Field mapping case.
            except:
                tryNum = ''
                hitId = req.params['hitId']
                commentsDisabled = ''
                mapHint = ''

        # Worker feedback and standalone cases.
        # These have no assignmentId.
        except:
            assignmentId = ''
            tryNum = ''
            hitId = ''
            resultsAccepted = ''
            submitTo = ''
            csrfToken = ''
            commentsDisabled = 'disabled'
            target = ''
            mapHint = ''

            # Worker feedback case.
            # This has a workerId.
            try:
                workerId = req.params['workerId']
                select = ''

            # Standalone case.
            # This has no workerId.
            except:
                workerId = ''
                select = buildSelect(mapc)

        # If mapping or training case,
        if len(assignmentId) > 0:
            # Mapping case.
            if len(hitId) > 0:
                k.write("getkml: Mapping request fetched %s kml = %s\n" % (kmlTypeDescr, kmlName))
                k.write("getkml: Mapping request hitId = %s\n" % hitId)
                k.write("getkml: Mapping request assignmentId = %s\n" % assignmentId)
            # Else, training case.
            else:
                k.write("getkml: Training request fetched %s kml = %s\n" % (kmlTypeDescr, kmlName))
                k.write("getkml: Training request assignmentId = %s\n" % assignmentId)
        # Else, worker feedback or standalone cases.
        else:
            if len(workerId) > 0:
                k.write("getkml: Worker feedback request fetched %s kml = %s\n" % (kmlTypeDescr, kmlName))
            else:
                k.write("getkml: Standalone request fetched %s kml = %s\n" % (kmlTypeDescr, kmlName))

        mainText = '''
            <!DOCTYPE html>
            <html>
                <head>
                    <title>500m Square Area in Africa</title>
                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
                    <link rel="stylesheet" href="https://openlayers.org/en/v3.18.2/css/ol.css" type="text/css">
                    <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Lato:300,400">
                    <!-- <link rel="stylesheet" href="/OL/fontello-799a171d/css/fontello.css" type="text/css" /> -->
                    <link rel="stylesheet" href="/OL/fontello-b8cf557f/css/fontello.css" type="text/css" />
                    <link rel="stylesheet" href="/OL/ol3-layerswitcher.css" type="text/css">
                    <link rel="stylesheet" href="/OL/controlbar.css" type="text/css">
                    <link rel="stylesheet" href="/OL/showkml.css" type="text/css">
                    <script src="https://openlayers.org/en/v3.18.2/build/ol.js" type="text/javascript"></script>
                    <!--<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"></script>-->
                    <script src="https://code.jquery.com/jquery-3.3.1.min.js"
                        integrity="sha256-FgpCb/KJQlLNfOu91ta32o/NMZxltwRo8QtmkMRdAu8="
                        crossorigin="anonymous">
                    </script>
                    <script type="text/javascript" src="/OL/ol3-layerswitcher.js"></script>
                    <script type="text/javascript" src="/OL/controlbar.js"></script>
                    <script type="text/javascript" src="/OL/buttoncontrol.js"></script>
                    <script type="text/javascript" src="/OL/togglecontrol.js"></script>
                    <script type="text/javascript" src="/OL/showkml.js"></script>
                </head>
                <body onload="init('%(kmlPath)s', '%(kmlName)s', '%(assignmentId)s', '%(tryNum)s', '%(resultsAccepted)s', '%(mapPath)s', '%(workerId)s')">
                    <form style='width:100%%;' name='mappingform' action='%(submitTo)s' method='POST' target='%(target)s'>
                        <div class='instructions'>
                            %(instructions)s
                        </div>
                        <table class='comments'><tr>
                        <th>
                            For comments, problems, or questions:
                        </th>
                        <td>
                            <input type='text'  class='comments' name='comment' size=80 maxlength=2048 %(commentsDisabled)s></input>
                        </td>
                        <th>
                            &nbsp;&nbsp;&nbsp;
                            <i>Hover over the icons in the toolbars below for usage instructions.</i>
                        </th>
                        </tr></table>
                        %(mapHint)s
                        %(csrfToken)s
                        <input type='hidden' name='kmlName' value='%(kmlName)s' />
                        <input type='hidden' name='hitId' value='%(hitId)s' />
                        <input type='hidden' name='assignmentId' value='%(assignmentId)s' />
                        <input type='hidden' name='tryNum' value='%(tryNum)s' />
                        <input type='hidden' name='savedMaps' />
                        <input type='hidden' name='kmlData' />
                    </form>
                    <div id="kml_display" style="width: 100%%; height: %(kmlMapHeight)spx;"></div>
                    <table id=labelBlock style="display: none; position:absolute; top:80px; left:40px;">
                        <tr><th>Category</th><td>%(select)s</td></tr>
                        <tr><th>Comment</th><td><textarea id="commentLabel"></textarea></td></tr>
                        <tr><th></th><td><button id="labelDone">Click when Done</button></td></tr>
                    </table>
                </body>
            </html>
        ''' % {
            'kmlPath': kmlGenUrl,
            'kmlName': kmlName,
            'hitId': hitId,
            'assignmentId': assignmentId,
            'tryNum': tryNum,
            'resultsAccepted': resultsAccepted,
            'submitTo': submitTo,
            'target': target,
            'instructions': instructions,
            'commentsDisabled': commentsDisabled,
            'mapHint': mapHint,
            'kmlMapHeight': kmlMapHeight,
            'mapPath': mapUrl,
            'workerId': workerId,
            'select': select,
            'csrfToken': csrfToken
        }
        res.text = mainText
    # No KML specified.
    else:
        mainText = '''
            <!DOCTYPE html>
            <html>
                <head>
                    <title>One Square Km in South Africa</title>
                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
                </head>
                <body>
                    <b>No KML specified in URL.</b>
                </body>
            </html>
        '''
        res.body = mainText
        k.write("getkml: No KML specified in URL.\n")
    del mapc
    k.close()
    return res(environ, start_response)
