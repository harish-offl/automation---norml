"""URL configuration and API views for the email automation project."""

import csv
import io
import os
import re
import threading

from django.http import FileResponse, JsonResponse
from django.urls import path
from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from campaign_runner import run_campaign
from .models import Lead


CSV_FIELD_ALIASES = {
    "name": "name",
    "full name": "name",
    "client name": "name",
    "email": "email",
    "e mail": "email",
    "email address": "email",
    "phone": "phone",
    "phone number": "phone",
    "mobile": "phone",
    "company": "company",
    "company name": "company",
    "industry": "industry",
    "solution": "niche",
    "service": "niche",
    "services": "niche",
    "service offering": "niche",
    "services offered": "niche",
    "offering": "niche",
    "offerings": "niche",
    "interest": "niche",
    "niche": "niche",
}


def _normalize_header(header):
    return re.sub(r"[^a-z0-9]+", " ", (header or "").strip().lower()).strip()


def _parse_bool(value, default=True):
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _canonicalize_row(row):
    normalized = {}
    ignored = []
    for key, value in row.items():
        canonical_key = CSV_FIELD_ALIASES.get(_normalize_header(key))
        if not canonical_key:
            ignored.append(key)
            continue
        normalized[canonical_key] = (value or "").strip()
    return normalized, ignored


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = "__all__"


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    parser_classes = (MultiPartParser,)

    @action(detail=False, methods=["post"])
    def upload(self, request):
        """Upload a CSV file of leads."""
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided"}, status=400)

        try:
            content = file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(content))
            replace_existing = _parse_bool(request.data.get("replace_existing"), default=True)
            require_solution = _parse_bool(request.data.get("require_solution"), default=True)
            parsed_rows = []
            ignored_columns = set()
            skipped = 0

            for row in reader:
                cleaned_row, ignored = _canonicalize_row(row)
                ignored_columns.update(ignored)

                email = cleaned_row.get("email")
                if not email:
                    skipped += 1
                    continue
                if require_solution and not cleaned_row.get("niche"):
                    skipped += 1
                    continue
                parsed_rows.append(cleaned_row)

            if not parsed_rows:
                return Response(
                    {
                        "error": "No valid rows found. Ensure CSV includes Email and Solution/Interest columns.",
                        "ignored_columns": sorted(ignored_columns),
                        "skipped": skipped,
                    },
                    status=400,
                )

            created = 0
            updated = 0
            with transaction.atomic():
                if replace_existing:
                    Lead.objects.all().delete()

                for row in parsed_rows:
                    defaults = {
                        "name": row.get("name", ""),
                        "niche": row.get("niche", ""),
                        "industry": row.get("industry", ""),
                        "phone": row.get("phone", ""),
                        "company": row.get("company", ""),
                    }
                    _, was_created = Lead.objects.update_or_create(email=row["email"], defaults=defaults)
                    if was_created:
                        created += 1
                    else:
                        updated += 1

            return Response(
                {
                    "created": created,
                    "updated": updated,
                    "skipped": skipped,
                    "replace_existing": replace_existing,
                    "require_solution": require_solution,
                    "ignored_columns": sorted(ignored_columns),
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=False, methods=["post"])
    def start_campaign(self, request):
        """Start a campaign in a background thread."""
        if not Lead.objects.exists():
            return Response({"error": "No leads found. Upload leads before starting a campaign."}, status=400)

        def task():
            run_campaign(use_csv_fallback=False)

        threading.Thread(target=task, daemon=True).start()
        return Response({"status": "campaign started"})


def frontend_view(request):
    """Serve the simple frontend page."""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(open(frontend_path, "rb"), content_type="text/html")
    return JsonResponse({"error": "Frontend not found"}, status=404)


urlpatterns = [
    path("api/leads/", LeadViewSet.as_view({"get": "list", "post": "create"})),
    path("api/leads/upload/", LeadViewSet.as_view({"post": "upload"})),
    path("api/campaign/start/", LeadViewSet.as_view({"post": "start_campaign"})),
    path("", frontend_view),
]
