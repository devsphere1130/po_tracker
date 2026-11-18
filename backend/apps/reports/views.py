import csv

from django.http import HttpResponse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


def _csv(name, result):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{name}.csv"'
    resp.write("﻿")  # BOM so Excel reads ₹ / UTF-8 correctly
    cols = result["columns"]
    w = csv.writer(resp)
    w.writerow([label for _, label in cols])
    for row in result["rows"]:
        w.writerow([row.get(key, "") for key, _ in cols])
    return resp


class ReportView(APIView):
    """GET /api/v1/reports/<name>/  (customers | materials | monthly | summary | po-status/<kind>)
    Filters: date_from, date_to, customer, material, status, limit, ordering. Add export=csv for a CSV file."""

    def get(self, request, name, kind=None):
        params = request.query_params
        if name == "summary":
            return Response(services.summary(params))
        if name == "po-status":
            result = services.po_list(params, kind or "")
            name = f"po-report-{kind}"
        elif name in services.REPORTS:
            result = services.REPORTS[name](params)
        else:
            raise NotFound("Unknown report.")
        if params.get("export") == "csv":
            return _csv(name, result)
        result["columns"] = [{"key": k, "label": l} for k, l in result["columns"]]
        return Response(result)
