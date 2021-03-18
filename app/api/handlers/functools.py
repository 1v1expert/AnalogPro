from django.http import JsonResponse


def make_error_json_response(description):
    return JsonResponse({"error": True, "description": description})


def make_success_json_response(body, **kwargs):
    return JsonResponse({"error": False, "body": body})
