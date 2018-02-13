#! /usr/bin/python

import os
import time
import smtplib
from datetime import datetime
from MappingCommon import MappingCommon

#
# Main code begins here.
#
fqaqcIssueCount = 0
nqaqcIssueCount = 0
issueFrequency = 60 * 60 * 12  # 12 hours

mapc = MappingCommon()

logFilePath = mapc.projectRoot + "/log"
k = open(logFilePath + "/createHit.log", "a+")

now = str(datetime.today())
k.write("\ncreateHit: Daemon starting up at %s\n" % now)
k.close()

# Execute loop based on polling interval
while True:
    hitPollingInterval = int(mapc.getConfiguration('Hit_PollingInterval'))
    availHitTarget = int(mapc.getConfiguration('AvailHitTarget'))
    qaqcHitPercentage = int(mapc.getConfiguration('QaqcHitPercentage'))
    fqaqcHitPercentage = int(mapc.getConfiguration('FqaqcHitPercentage'))
    hitActiveAssignPercentF = int(mapc.getConfiguration('Hit_ActiveAssignPercentF'))
    hitActiveAssignPercentN = int(mapc.getConfiguration('Hit_ActiveAssignPercentN'))

    k = open(logFilePath + "/createHit.log", "a+")
    now = str(datetime.today())

    # Determine the number of QAQC, FQAQC and NQAQC HITs that should exist.
    numAvailQaqcHits = int(round(float(availHitTarget * qaqcHitPercentage) / 100.))
    numAvailFqaqcHits = int(round(float(availHitTarget * fqaqcHitPercentage) / 100.))
    numAvailNonQaqcHits = availHitTarget - numAvailQaqcHits - numAvailFqaqcHits

    # Get all HITs.
    hits = mapc.getAllHits()

    # Do the verification.
    numQaqcHits = 0
    numFqaqcHits = 0
    numNonQaqcHits = 0
    for hitId, row in hits.iteritems():
        # Calculate the nuumber of assignable QAQC, FQAQC, and NQAQC HITs 
        # currently active. For HITs with multiple assignments,
        # only count HITs whose number of completed assignments does not exceed
        # the configured threshold.
        maxAssignments1 = row['maxAssignments'] - 1
        if row['kmlType'] == MappingCommon.KmlQAQC:
            if row['assignmentsCompleted'] <= maxAssignments1:
                numQaqcHits = numQaqcHits + 1
        elif row['kmlType'] == MappingCommon.KmlFQAQC:
            threshold = int(round(float(hitActiveAssignPercentF * maxAssignments1) / 100.))
            if row['assignmentsCompleted'] <= threshold:
                numFqaqcHits = numFqaqcHits + 1
        elif row['kmlType'] == MappingCommon.KmlNormal:
            threshold = int(round(float(hitActiveAssignPercentN * maxAssignments1) / 100.))
            if row['assignmentsCompleted'] <= threshold:
                numNonQaqcHits = numNonQaqcHits + 1

    # Create any needed QAQC HITs.
    kmlType = MappingCommon.KmlQAQC
    numReqdQaqcHits = max(numAvailQaqcHits - numQaqcHits, 0)
    if numReqdQaqcHits > 0:
        k.write("\ncreateHit: datetime = %s\n" % now)
        k.write("createHit: createHit sees %s QAQC HITs, and needs to create %s HITs\n" % 
            (numQaqcHits, numReqdQaqcHits))

    for i in xrange(numReqdQaqcHits):
        # Retrieve the last kml gid used to create a QAQC HIT.
        curQaqcGid = mapc.getSystemData('CurQaqcGid')

        # Select the next kml for which to create a HIT. 
        # Look for all kmls of the right type whose gid is greater than the last kml chosen.
        # Exclude any kmls that are currently associated with an active HIT.
        mapc.cur.execute("""
            select name, gid, fwts 
            from kml_data k 
            where not exists (select true from hit_data h 
                where h.name = k.name and delete_time is null)
            and  kml_type = '%s' 
            and gid > %s 
            order by gid 
            limit 1""" % (kmlType, curQaqcGid))
        row = mapc.cur.fetchone()
        # If we have no kmls left, loop back to the beginning of the table.
        if not row:
            curQaqcGid = 0
            mapc.cur.execute("""
                select name, gid, fwts from kml_data k 
                where not exists (select true from hit_data h 
                    where h.name = k.name and delete_time is null)
                and  kml_type = '%s' 
                and gid > %s 
                order by gid 
                limit 1""" % (kmlType, curQaqcGid))
            row = mapc.cur.fetchone()
            # If we still have no kmls left, all kmls are in use as HITs.
            # Try again later.
            if not row:
                break
        nextKml = row[0]
        gid = row[1]
        fwts = row[2]
        mapc.setSystemData('CurQaqcGid', gid)

        # Create the QAQC HIT
        hitId = mapc.createHit(nextKml, fwts=fwts)
        k.write("createHit: Created HIT ID %s for QAQC KML %s\n" % (hitId, nextKml))

    # Create any needed FQAQC HITs.
    kmlType = MappingCommon.KmlFQAQC
    numReqdFqaqcHits = max(numAvailFqaqcHits - numFqaqcHits, 0)
    if numReqdFqaqcHits > 0:
        k.write("\ncreateHit: datetime = %s\n" % now)
        k.write("createHit: createHit sees %s FQAQC HITs, and needs to create %s HITs\n" % 
            (numFqaqcHits, numReqdFqaqcHits))

    for i in xrange(numReqdFqaqcHits):
        # Select the next kml for which to create a HIT. 
        # Look for all kmls of the right type whose mapped count by a trusted worker is less than
        # the number of mappings specified by Hit_MaxAssignmentsF.
        # Exclude any kmls that are currently associated with an active HIT.
        hitMaxAssignmentsF = int(mapc.getConfiguration('Hit_MaxAssignmentsF'))
        mapc.cur.execute("""
            select name, mapped_count, fwts 
            from kml_data k 
            where not exists (select true from hit_data h 
                where h.name = k.name and delete_time is null)
            and  kml_type = '%s' 
            and mapped_count < %s
            order by gid 
            limit 1""" % (kmlType, hitMaxAssignmentsF))
        row = mapc.cur.fetchone()
        # If we have no kmls left, all kmls in the kml_data table have been 
        # successfully processed. Notify Lyndon that more kmls are needed.
        if not row:
            if (fqaqcIssueCount % (issueFrequency / hitPollingInterval)) == 0:
                k.write("createHit: Alert: all FQAQC KMLs in kml_data table have been successfully processed. More KMLs needed to create more HITs of this type.\n")
                mapc.createIssue(mapc, "No FQAQC KMLs in kml_data table", 
                        "Alert: all FQAQC KMLs in kml_data table have been successfully processed. More KMLs needed to create more HITs of this type.", 
                        MappingCommon.AlertIssue)
            fqaqcIssueCount += 1
            break
        else:
            if (fqaqcIssueCount % (issueFrequency / hitPollingInterval)) == 0:
                fqaqcIssueCount = 0
            else:
                fqaqcIssueCount += 1
        nextKml = row[0]
        fwts = row[2]
        remainingAssignments = hitMaxAssignmentsF - row[1]

        # Create the FQAQC HIT
        hitId = mapc.createHit(nextKml, fwts=fwts, maxAssignments=remainingAssignments)
        k.write("createHit: Created HIT ID %s with %d assignments for FQAQC KML %s\n" % 
                (hitId, remainingAssignments, nextKml))

    # Create any needed NQAQC HITs.
    kmlType = MappingCommon.KmlNormal
    numReqdNonQaqcHits = max(numAvailNonQaqcHits - numNonQaqcHits, 0)
    if numReqdNonQaqcHits > 0:
        k.write("\ncreateHit: datetime = %s\n" % now)
        k.write("createHit: createHit sees %s NQAQC HITs, and needs to create %s HITs\n" % 
            (numNonQaqcHits, numReqdNonQaqcHits))

    for i in xrange(numReqdNonQaqcHits):
        # Select the next kml for which to create a HIT. 
        # Look for all kmls of the right type whose mapped count by a trusted worker is less than
        # the number of mappings specified by Hit_MaxAssignmentsN.
        # Exclude any kmls that are currently associated with an active HIT.
        hitMaxAssignmentsN = int(mapc.getConfiguration('Hit_MaxAssignmentsN'))
        mapc.cur.execute("""
            select name, mapped_count, fwts 
            from kml_data k 
            where not exists (select true from hit_data h 
                where h.name = k.name and delete_time is null)
            and  kml_type = '%s' 
            and mapped_count < %s
            order by gid 
            limit 1""" % (kmlType, hitMaxAssignmentsN))
        row = mapc.cur.fetchone()
        # If we have no kmls left, all kmls in the kml_data table have been 
        # successfully processed. Notify Lyndon that more kmls are needed.
        if not row:
            if (nqaqcIssueCount % (issueFrequency / hitPollingInterval)) == 0:
                k.write("createHit: Alert: all NQAQC KMLs in kml_data table have been successfully processed. More KMLs needed to create more HITs of this type.\n")
                mapc.createIssue(mapc, "No NQAQC KMLs in kml_data table", 
                        "Alert: all NQAQC KMLs in kml_data table have been successfully processed. More KMLs needed to create more HITs of this type.", 
                        MappingCommon.AlertIssue)
            nqaqcIssueCount += 1
            break
        else:
            if (nqaqcIssueCount % (issueFrequency / hitPollingInterval)) == 0:
                nqaqcIssueCount = 0
            else:
                nqaqcIssueCount += 1
        nextKml = row[0]
        fwts = row[2]
        remainingAssignments = hitMaxAssignmentsN - row[1]

        # Create the NQAQC HIT
        hitId = mapc.createHit(nextKml, fwts=fwts, maxAssignments=remainingAssignments)
        k.write("createHit: Created HIT ID %s with %d assignments for NQAQC KML %s\n" % 
                (hitId, remainingAssignments, nextKml))

    # Sleep for specified polling interval
    k.close()
    time.sleep(hitPollingInterval)
