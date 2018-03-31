from webob import Request, Response
import datetime
from MappingCommon import MappingCommon

def application(environ, start_response):
    req = Request(environ)
    res = Response()
    res.content_type = 'text/html'

    now = str(datetime.datetime.today())

    mapc = MappingCommon()
    logFilePath = mapc.projectRoot + "/log"
    mturkFrameHeight = int(mapc.getConfiguration('MTurkFrameHeight'))
    kmlUrl = mapc.getConfiguration('KMLUrl')
    apiUrl = mapc.getConfiguration('APIUrl')
    mapUrl = mapc.getConfiguration('MapUrl')
    mturkPostPolygonScript = mapc.getConfiguration('MTurkPostPolygonScript')
    mturkNoPolygonScript = mapc.getConfiguration('MTurkNoPolygonScript')
    instructions = mapc.getConfiguration('KMLInstructions')

    polygonUrl = apiUrl + '/' + mturkPostPolygonScript
    noPolygonUrl = apiUrl + '/' + mturkNoPolygonScript
    headerHeight = 80
    mapHeight = mturkFrameHeight - headerHeight

    k = open(logFilePath + "/OL.log", "a")
    k.write("\ngetkml: datetime = %s\n" % now)

    kmlName = req.params['kmlName']
    if len(kmlName) > 0:
        kmlTypeDescr = mapc.getKmlTypeDescription(kmlName)
        mapHint = mapc.querySingleValue("select hint from kml_data where name = '%s'" % kmlName)

        # Training and field mapping cases.
        # These have an assignmentId.
        try:
            assignmentId = req.params['assignmentId']
            resultsAccepted = req.params['resultsAccepted']
            submitTo = req.params['submitTo']
            csrfToken = req.params['csrfToken']
            workerId = ''

            # Training case.
            # This has a tryNum.
            try:
                tryNum = int(req.params['tryNum'])
                commentsDisabled = 'disabled'
                target = '_parent'
                mapHint = '<div class="hints">Hint: %s</div>' % mapHint

                headerHeight = headerHeight + 20
                mapHeight = mturkFrameHeight - headerHeight

            # Field mapping case.
            except:
                tryNum = 0
                commentsDisabled = ''
                target = '_self'
                mapHint = ''

        # Worker feedback and standalone cases.
        # These have no assignmentId.
        except:
            assignmentId = ''
            tryNum = 0
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

            # Standalone case.
            # This has no workerId.
            except:
                workerId = ''

        # If mapping or training case,
        if len(assignmentId) > 0:
            # Mapping case.
            if tryNum == 0:
                k.write("getkml: Mapping request fetched %s kml = %s\n" % (kmlTypeDescr, kmlName))
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
                    <link rel="stylesheet" href="/OL/fontello-799a171d/css/fontello.css" type="text/css" />
                    <link rel="stylesheet" href="/OL/ol3-layerswitcher.css" type="text/css">
                    <link rel="stylesheet" href="/OL/controlbar.css" type="text/css">
                    <link rel="stylesheet" href="/OL/showkml.css" type="text/css">
                    <script src="https://openlayers.org/en/v3.18.2/build/ol.js" type="text/javascript"></script>
                    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"></script>
                    <script type="text/javascript" src="/OL/ol3-layerswitcher.js"></script>
                    <script type="text/javascript" src="/OL/controlbar.js"></script>
                    <script type="text/javascript" src="/OL/buttoncontrol.js"></script>
                    <script type="text/javascript" src="/OL/togglecontrol.js"></script>
                    <script type="text/javascript" src="/OL/showkml.js"></script>
                    <style>
                        html, body {
                            height: %(mturkFrameHeight)spx;
                        }
                    </style>
                </head>
                <body onload="init('%(kmlPath)s', '%(polygonPath)s', '%(noPolygonPath)s', '%(kmlName)s', '%(assignmentId)s', '%(tryNum)s', '%(resultsAccepted)s', '%(mapPath)s', '%(workerId)s')">
                    <form style='width: 100%%; height: %(headerHeight)spx;' name='mappingform' action='%(submitTo)s' method='POST' target='%(target)s'>
                        %(csrfToken)s
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
                        <input type='hidden' name='kmlName' value='%(kmlName)s' />
                        <input type='hidden' name='assignmentId' value='%(assignmentId)s' />
                        <input type='hidden' name='tryNum' value='%(tryNum)s' />
                        <input type='hidden' name='kmlData' />
                    </form>
                    <div id="kml_display" style="width: 100%%; height: %(mapHeight)spx;"></div>
                </body>
            </html>
        ''' % {
            'kmlPath': kmlUrl,
            'polygonPath': polygonUrl,
            'noPolygonPath': noPolygonUrl,
            'kmlName': kmlName,
            'assignmentId': assignmentId,
            'tryNum': tryNum,
            'resultsAccepted': resultsAccepted,
            'submitTo': submitTo,
            'target': target,
            'instructions': instructions,
            'commentsDisabled': commentsDisabled,
            'mapHint': mapHint,
            'mturkFrameHeight': mturkFrameHeight,
            'headerHeight': headerHeight,
            'mapHeight': mapHeight,
            'mapPath': mapUrl,
            'workerId': workerId,
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
